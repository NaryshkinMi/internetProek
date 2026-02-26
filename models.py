from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Ассоциативная таблица для связи задачи и тега (многие-ко-многим)
task_tags = db.Table('task_tags',
                     db.Column('task_id', db.Integer, db.ForeignKey('task.id'), primary_key=True),
                     db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
                     )

# Ассоциативная таблица для совместного доступа к задачам
task_shared = db.Table('task_shared',
                       db.Column('task_id', db.Integer, db.ForeignKey('task.id'), primary_key=True),
                       db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
                       db.Column('permission', db.String(20), default='view'),
                       db.Column('shared_at', db.DateTime, default=datetime.utcnow)
                       )


class User(UserMixin, db.Model):
    """Модель пользователя"""
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    avatar = db.Column(db.String(200), default='/static/default-avatar.png')

    # Связи
    tasks = db.relationship('Task', backref='owner', lazy=True,
                            foreign_keys='Task.user_id', cascade='all, delete-orphan')
    categories = db.relationship('Category', backref='user', lazy=True, cascade='all, delete-orphan')
    tags = db.relationship('Tag', backref='user', lazy=True, cascade='all, delete-orphan')

    # Задачи, доступные для совместного использования
    shared_tasks = db.relationship('Task', secondary=task_shared, lazy='subquery',
                                   backref=db.backref('shared_with', lazy=True))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Category(db.Model):
    """Категория задач"""
    __tablename__ = 'category'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(7), default='#667eea')
    icon = db.Column(db.String(50), default='📁')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связь с задачами
    tasks = db.relationship('Task', backref='category', lazy=True)

    __table_args__ = (db.UniqueConstraint('name', 'user_id', name='unique_category_per_user'),)


class Tag(db.Model):
    """Тег для задач"""
    __tablename__ = 'tag'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False)
    color = db.Column(db.String(7), default='#48bb78')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связь с задачами (многие-ко-многим)
    tasks = db.relationship('Task', secondary=task_tags, lazy='subquery',
                            backref=db.backref('tags', lazy=True))

    __table_args__ = (db.UniqueConstraint('name', 'user_id', name='unique_tag_per_user'),)


class Task(db.Model):
    """Модель задачи"""
    __tablename__ = 'task'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Приоритет (1 - низкий, 2 - средний, 3 - высокий, 4 - критический)
    priority = db.Column(db.Integer, default=2)

    # Статус
    status = db.Column(db.String(20), default='active')

    # Внешние ключи
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)

    def get_priority_name(self):
        priorities = {1: 'Низкий', 2: 'Средний', 3: 'Высокий', 4: 'Критический'}
        return priorities.get(self.priority, 'Средний')

    def get_priority_color(self):
        colors = {1: '#718096', 2: '#48bb78', 3: '#ecc94b', 4: '#f56565'}
        return colors.get(self.priority, '#48bb78')

    def get_priority_class(self):
        classes = {1: 'priority-low', 2: 'priority-medium', 3: 'priority-high', 4: 'priority-critical'}
        return classes.get(self.priority, 'priority-medium')

    def get_status_badge(self):
        badges = {
            'active': 'primary',
            'completed': 'success',
            'archived': 'secondary'
        }
        return badges.get(self.status, 'primary')