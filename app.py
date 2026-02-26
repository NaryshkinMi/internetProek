import os
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Task
from forms import LoginForm, RegistrationForm, TaskForm

# Загружаем переменные окружения из .env файла
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///tasks.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализируем базу данных
db.init_app(app)

# Настройка Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'
login_manager.login_message_category = 'info'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Создание таблиц базы данных
with app.app_context():
    db.create_all()


@app.route('/')
def index():
    """Главная страница"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/dashboard')
@login_required
def dashboard():
    """Панель управления с задачами"""
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.due_date).all()
    now = datetime.now().date()
    return render_template('dashboard.html', tasks=tasks, now=now)


@app.route('/calendar')
@login_required
def calendar():
    """Календарь с задачами"""
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    return render_template('calendar.html', tasks=tasks)


@app.route('/task/add', methods=['GET', 'POST'])
@login_required
def add_task():
    """Добавление новой задачи"""
    form = TaskForm()
    if form.validate_on_submit():
        task = Task(
            title=form.title.data,
            description=form.description.data,
            due_date=form.due_date.data,
            user_id=current_user.id
        )
        db.session.add(task)
        db.session.commit()
        flash('Задача успешно добавлена!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_task.html', form=form)


@app.route('/task/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_task(id):
    """Редактирование задачи"""
    task = Task.query.get_or_404(id)

    # Проверяем, принадлежит ли задача текущему пользователю
    if task.user_id != current_user.id:
        flash('У вас нет прав для редактирования этой задачи', 'danger')
        return redirect(url_for('dashboard'))

    form = TaskForm(obj=task)
    if form.validate_on_submit():
        task.title = form.title.data
        task.description = form.description.data
        task.due_date = form.due_date.data
        db.session.commit()
        flash('Задача обновлена!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_task.html', form=form, task=task)


@app.route('/task/delete/<int:id>')
@login_required
def delete_task(id):
    """Удаление задачи"""
    task = Task.query.get_or_404(id)

    if task.user_id == current_user.id:
        db.session.delete(task)
        db.session.commit()
        flash('Задача удалена', 'success')
    else:
        flash('У вас нет прав для удаления этой задачи', 'danger')

    return redirect(url_for('dashboard'))


@app.route('/task/toggle/<int:id>')
@login_required
def toggle_task(id):
    """Отметить задачу как выполненную/невыполненную"""
    task = Task.query.get_or_404(id)

    if task.user_id == current_user.id:
        task.completed = not task.completed
        db.session.commit()
        flash(f'Задача {"выполнена" if task.completed else "возобновлена"}', 'success')
    else:
        flash('У вас нет прав для изменения этой задачи', 'danger')

    return redirect(url_for('dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Вход пользователя"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Добро пожаловать!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')

    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация нового пользователя"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        # Проверяем, существует ли пользователь
        if User.query.filter_by(username=form.username.data).first():
            flash('Имя пользователя уже занято', 'danger')
            return render_template('register.html', form=form)

        if User.query.filter_by(email=form.email.data).first():
            flash('Email уже зарегистрирован', 'danger')
            return render_template('register.html', form=form)

        # Создаём нового пользователя
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
    """Выход пользователя"""
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))


# Команда для инициализации базы данных
@app.cli.command('init-db')
def init_db():
    """Инициализация базы данных"""
    db.create_all()
    print('✅ База данных инициализирована!')


if __name__ == '__main__':
    app.run(debug=True)