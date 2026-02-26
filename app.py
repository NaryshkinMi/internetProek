import os
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import or_
from models import db, User, Task, Category, Tag, task_shared
from forms import LoginForm, RegistrationForm, TaskForm, CategoryForm, TagForm, ShareTaskForm
from filters import init_filters

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///tasks.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'
login_manager.login_message_category = 'info'

# Инициализация пользовательских фильтров
init_filters(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Создание таблиц
with app.app_context():
    db.create_all()


# Контекстный процессор для передачи текущей даты в шаблоны
@app.context_processor
def inject_now():
    return {'now': datetime.now().date()}


# ==================== ГЛАВНЫЕ СТРАНИЦЫ ====================

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/dashboard')
@login_required
def dashboard():
    # Получаем параметры фильтрации
    filter_status = request.args.get('status', 'active')
    filter_category = request.args.get('category', 'all')
    filter_priority = request.args.get('priority', 'all')

    # Базовый запрос
    query = Task.query.filter_by(user_id=current_user.id)

    # Применяем фильтры
    if filter_status != 'all':
        query = query.filter_by(status=filter_status)

    if filter_category != 'all' and filter_category.isdigit():
        query = query.filter_by(category_id=int(filter_category))

    if filter_priority != 'all' and filter_priority.isdigit():
        query = query.filter_by(priority=int(filter_priority))

    tasks = query.order_by(Task.priority.desc(), Task.due_date).all()

    # Получаем категории и теги для фильтров
    categories = Category.query.filter_by(user_id=current_user.id).all()
    tags = Tag.query.filter_by(user_id=current_user.id).all()

    # Статистика
    stats = {
        'total': Task.query.filter_by(user_id=current_user.id).count(),
        'active': Task.query.filter_by(user_id=current_user.id, status='active').count(),
        'completed': Task.query.filter_by(user_id=current_user.id, status='completed').count(),
        'overdue': Task.query.filter(
            Task.user_id == current_user.id,
            Task.status == 'active',
            Task.due_date < datetime.now().date()
        ).count()
    }

    return render_template('dashboard.html',
                           tasks=tasks,
                           categories=categories,
                           tags=tags,
                           stats=stats,
                           filter_status=filter_status,
                           filter_category=filter_category,
                           filter_priority=filter_priority)


@app.route('/calendar')
@login_required
def calendar():
    tasks = Task.query.filter(
        Task.user_id == current_user.id,
        Task.due_date.isnot(None)
    ).all()

    # Также добавляем задачи, к которым есть доступ
    shared_tasks = db.session.query(Task).join(
        task_shared, (task_shared.c.task_id == Task.id)
    ).filter(task_shared.c.user_id == current_user.id).all()

    all_tasks = tasks + shared_tasks

    return render_template('calendar.html', tasks=all_tasks)


# ==================== УПРАВЛЕНИЕ ЗАДАЧАМИ ====================

@app.route('/task/add', methods=['GET', 'POST'])
@login_required
def add_task():
    form = TaskForm()

    # Заполняем выпадающий список категорий
    categories = Category.query.filter_by(user_id=current_user.id).all()
    form.category_id.choices = [(0, 'Без категории')] + [(c.id, f"{c.icon} {c.name}") for c in categories]

    if form.validate_on_submit():
        # Обработка тегов
        tag_names = [t.strip() for t in form.tags.data.split(',')] if form.tags.data else []
        tags = []
        for tag_name in tag_names:
            if tag_name:
                tag = Tag.query.filter_by(user_id=current_user.id, name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name, user_id=current_user.id)
                    db.session.add(tag)
                tags.append(tag)

        task = Task(
            title=form.title.data,
            description=form.description.data,
            due_date=form.due_date.data,
            priority=int(form.priority.data),
            status=form.status.data,
            user_id=current_user.id,
            category_id=form.category_id.data if form.category_id.data != 0 else None
        )

        task.tags = tags
        db.session.add(task)
        db.session.commit()

        flash('Задача успешно создана!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('task/add.html', form=form)


@app.route('/task/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_task(id):
    task = Task.query.get_or_404(id)

    # Проверка прав доступа
    if task.user_id != current_user.id:
        # Проверяем, есть ли доступ на редактирование
        shared = db.session.query(task_shared).filter_by(
            task_id=id, user_id=current_user.id, permission='edit'
        ).first()
        if not shared:
            abort(403)

    form = TaskForm(obj=task)

    # Заполняем выпадающий список категорий
    categories = Category.query.filter_by(user_id=current_user.id).all()
    form.category_id.choices = [(0, 'Без категории')] + [(c.id, f"{c.icon} {c.name}") for c in categories]

    # Заполняем теги
    if request.method == 'GET':
        form.tags.data = ', '.join([tag.name for tag in task.tags])
        form.priority.data = str(task.priority)

    if form.validate_on_submit():
        task.title = form.title.data
        task.description = form.description.data
        task.due_date = form.due_date.data
        task.priority = int(form.priority.data)
        task.status = form.status.data
        task.category_id = form.category_id.data if form.category_id.data != 0 else None

        # Обновляем теги
        tag_names = [t.strip() for t in form.tags.data.split(',')] if form.tags.data else []
        tags = []
        for tag_name in tag_names:
            if tag_name:
                tag = Tag.query.filter_by(user_id=current_user.id, name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name, user_id=current_user.id)
                    db.session.add(tag)
                tags.append(tag)

        task.tags = tags
        task.updated_at = datetime.utcnow()

        if task.status == 'completed' and not task.completed_at:
            task.completed_at = datetime.utcnow()

        db.session.commit()
        flash('Задача обновлена!', 'success')
        return redirect(url_for('view_task', id=task.id))

    return render_template('task/edit.html', form=form, task=task)


@app.route('/task/<int:id>')
@login_required
def view_task(id):
    task = Task.query.get_or_404(id)

    # Проверка прав доступа
    if task.user_id != current_user.id:
        shared = db.session.query(task_shared).filter_by(
            task_id=id, user_id=current_user.id
        ).first()
        if not shared:
            abort(403)
        can_edit = shared.permission == 'edit'
    else:
        can_edit = True

    return render_template('task/view.html', task=task, can_edit=can_edit)


@app.route('/task/delete/<int:id>')
@login_required
def delete_task(id):
    task = Task.query.get_or_404(id)

    if task.user_id != current_user.id:
        abort(403)

    db.session.delete(task)
    db.session.commit()
    flash('Задача удалена', 'success')
    return redirect(url_for('dashboard'))


@app.route('/task/toggle/<int:id>')
@login_required
def toggle_task(id):
    task = Task.query.get_or_404(id)

    if task.user_id != current_user.id:
        shared = db.session.query(task_shared).filter_by(
            task_id=id, user_id=current_user.id, permission='edit'
        ).first()
        if not shared:
            abort(403)

    if task.status == 'completed':
        task.status = 'active'
        task.completed_at = None
    else:
        task.status = 'completed'
        task.completed_at = datetime.utcnow()

    task.completed = not task.completed
    db.session.commit()

    return redirect(request.referrer or url_for('dashboard'))


# ==================== УПРАВЛЕНИЕ КАТЕГОРИЯМИ ====================

@app.route('/categories')
@login_required
def list_categories():
    categories = Category.query.filter_by(user_id=current_user.id).all()
    return render_template('category/list.html', categories=categories)


@app.route('/category/add', methods=['GET', 'POST'])
@login_required
def add_category():
    form = CategoryForm()

    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            color=form.color.data,
            icon=form.icon.data,
            user_id=current_user.id
        )
        db.session.add(category)
        db.session.commit()
        flash('Категория создана!', 'success')
        return redirect(url_for('list_categories'))

    return render_template('category/add.html', form=form)


@app.route('/category/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    category = Category.query.get_or_404(id)

    if category.user_id != current_user.id:
        abort(403)

    form = CategoryForm(obj=category)

    if form.validate_on_submit():
        category.name = form.name.data
        category.color = form.color.data
        category.icon = form.icon.data
        db.session.commit()
        flash('Категория обновлена!', 'success')
        return redirect(url_for('list_categories'))

    return render_template('category/edit.html', form=form, category=category)


@app.route('/category/delete/<int:id>')
@login_required
def delete_category(id):
    category = Category.query.get_or_404(id)

    if category.user_id != current_user.id:
        abort(403)

    # Обновляем задачи, убирая категорию
    Task.query.filter_by(category_id=id).update({Task.category_id: None})

    db.session.delete(category)
    db.session.commit()
    flash('Категория удалена', 'success')
    return redirect(url_for('list_categories'))


# ==================== УПРАВЛЕНИЕ ТЕГАМИ ====================

@app.route('/tags')
@login_required
def list_tags():
    """Список тегов"""
    tags = Tag.query.filter_by(user_id=current_user.id).all()
    return render_template('tag/list.html', tags=tags)


@app.route('/tag/add', methods=['GET', 'POST'])
@login_required
def add_tag():
    """Добавление нового тега"""
    form = TagForm()

    if form.validate_on_submit():
        # Проверяем, существует ли уже такой тег
        existing = Tag.query.filter_by(user_id=current_user.id, name=form.name.data).first()
        if existing:
            flash('Тег с таким именем уже существует', 'danger')
            return render_template('tag/add.html', form=form)

        tag = Tag(
            name=form.name.data,
            color=form.color.data,
            user_id=current_user.id
        )
        db.session.add(tag)
        db.session.commit()
        flash('Тег создан!', 'success')
        return redirect(url_for('list_tags'))

    return render_template('tag/add.html', form=form)


@app.route('/tag/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_tag(id):
    """Редактирование тега"""
    tag = Tag.query.get_or_404(id)

    if tag.user_id != current_user.id:
        abort(403)

    form = TagForm(obj=tag)

    if form.validate_on_submit():
        # Проверяем, не занято ли имя другим тегом
        existing = Tag.query.filter_by(user_id=current_user.id, name=form.name.data).first()
        if existing and existing.id != id:
            flash('Тег с таким именем уже существует', 'danger')
            return render_template('tag/edit.html', form=form, tag=tag)

        tag.name = form.name.data
        tag.color = form.color.data
        db.session.commit()
        flash('Тег обновлен!', 'success')
        return redirect(url_for('list_tags'))

    return render_template('tag/edit.html', form=form, tag=tag)


@app.route('/tag/delete/<int:id>')
@login_required
def delete_tag(id):
    """Удаление тега"""
    tag = Tag.query.get_or_404(id)

    if tag.user_id != current_user.id:
        abort(403)

    # Удаляем связи с задачами (автоматически через cascade)
    db.session.delete(tag)
    db.session.commit()
    flash('Тег удален', 'success')
    return redirect(url_for('list_tags'))


# ==================== СОВМЕСТНАЯ РАБОТА ====================

@app.route('/task/<int:id>/share', methods=['GET', 'POST'])
@login_required
def share_task(id):
    task = Task.query.get_or_404(id)

    if task.user_id != current_user.id:
        abort(403)

    form = ShareTaskForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if not user:
            flash('Пользователь с таким email не найден', 'danger')
            return render_template('task/share.html', form=form, task=task)

        if user.id == current_user.id:
            flash('Нельзя поделиться задачей с самим собой', 'warning')
            return render_template('task/share.html', form=form, task=task)

        # Проверяем, не поделились ли уже
        existing = db.session.query(task_shared).filter_by(
            task_id=id, user_id=user.id
        ).first()

        if existing:
            flash('Задача уже доступна этому пользователю', 'info')
            return redirect(url_for('view_task', id=task.id))

        # Добавляем запись о совместном доступе
        stmt = task_shared.insert().values(
            task_id=id,
            user_id=user.id,
            permission=form.permission.data
        )
        db.session.execute(stmt)
        db.session.commit()

        flash(f'Задача доступна пользователю {user.username}', 'success')
        return redirect(url_for('view_task', id=task.id))

    # Получаем список пользователей, с кем уже поделились
    shared_users = db.session.query(User).join(
        task_shared, (task_shared.c.user_id == User.id)
    ).filter(task_shared.c.task_id == id).all()

    return render_template('task/share.html', form=form, task=task, shared_users=shared_users)


@app.route('/task/<int:id>/revoke/<int:user_id>')
@login_required
def revoke_access(id, user_id):
    task = Task.query.get_or_404(id)

    if task.user_id != current_user.id:
        abort(403)

    stmt = task_shared.delete().where(
        task_shared.c.task_id == id,
        task_shared.c.user_id == user_id
    )
    db.session.execute(stmt)
    db.session.commit()

    flash('Доступ отозван', 'success')
    return redirect(url_for('share_task', id=id))


@app.route('/shared-with-me')
@login_required
def shared_with_me():
    # Получаем задачи с доступом
    tasks_with_permission = db.session.query(
        Task, task_shared.c.permission
    ).join(
        task_shared, (task_shared.c.task_id == Task.id)
    ).filter(task_shared.c.user_id == current_user.id).all()

    # Преобразуем в список словарей для удобства
    tasks = []
    for task, permission in tasks_with_permission:
        task_data = {
            'task': task,
            'permission': permission
        }
        tasks.append(task_data)

    return render_template('shared_tasks.html', tasks=tasks)


# ==================== API ДЛЯ БЫСТРЫХ ДЕЙСТВИЙ ====================

@app.route('/api/tasks/quick-add', methods=['POST'])
@login_required
def quick_add_task():
    data = request.get_json()

    task = Task(
        title=data.get('title'),
        user_id=current_user.id,
        priority=2,
        status='active'
    )

    db.session.add(task)
    db.session.commit()

    return jsonify({'id': task.id, 'title': task.title})


@app.route('/api/tasks/search')
@login_required
def search_tasks():
    query = request.args.get('q', '')

    if not query or len(query) < 2:
        return jsonify([])

    tasks = Task.query.filter(
        Task.user_id == current_user.id,
        or_(
            Task.title.ilike(f'%{query}%'),
            Task.description.ilike(f'%{query}%')
        )
    ).limit(10).all()

    return jsonify([{
        'id': t.id,
        'title': t.title,
        'status': t.status,
        'priority': t.priority
    } for t in tasks])


# ==================== АУТЕНТИФИКАЦИЯ ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash(f'С возвращением, {user.username}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')

    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Имя пользователя уже занято', 'danger')
            return render_template('register.html', form=form)

        if User.query.filter_by(email=form.email.data).first():
            flash('Email уже зарегистрирован', 'danger')
            return render_template('register.html', form=form)

        user = User(
            username=form.username.data,
            email=form.email.data
        )
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()

        flash('Регистрация успешна! Теперь вы можете войти', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))


@app.cli.command('init-db')
def init_db():
    db.create_all()
    print('✅ База данных инициализирована!')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)