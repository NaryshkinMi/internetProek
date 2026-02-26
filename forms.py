from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, DateField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional
from wtforms.widgets import TextArea


class LoginForm(FlaskForm):
    """Форма входа"""
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember = BooleanField('Запомнить меня')


class RegistrationForm(FlaskForm):
    """Форма регистрации"""
    username = StringField('Имя пользователя',
                          validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email',
                       validators=[DataRequired(), Email()])
    password = PasswordField('Пароль',
                            validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Повторите пароль',
                             validators=[DataRequired(), EqualTo('password')])


class TaskForm(FlaskForm):
    """Форма задачи"""
    title = StringField('Название задачи',
                       validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Описание',
                               validators=[Optional(), Length(max=5000)],
                               widget=TextArea())
    due_date = DateField('Дата выполнения',
                        format='%Y-%m-%d',
                        validators=[Optional()])
    priority = SelectField('Приоритет',
                          choices=[('1', 'Низкий'), ('2', 'Средний'), ('3', 'Высокий'), ('4', 'Критический')],
                          default='2')
    category_id = SelectField('Категория', coerce=int, validators=[Optional()])
    tags = StringField('Теги (через запятую)', validators=[Optional()])
    status = SelectField('Статус',
                        choices=[('active', 'Активная'), ('completed', 'Выполнена'), ('archived', 'В архиве')],
                        default='active')


class CategoryForm(FlaskForm):
    """Форма категории"""
    name = StringField('Название категории', validators=[DataRequired(), Length(max=50)])
    color = StringField('Цвет (HEX)', validators=[DataRequired(), Length(max=7)], default='#667eea')
    icon = StringField('Иконка (эмодзи)', validators=[Optional(), Length(max=10)], default='📁')


class TagForm(FlaskForm):
    """Форма тега"""
    name = StringField('Название тега', validators=[DataRequired(), Length(max=30)])
    color = StringField('Цвет (HEX)', validators=[DataRequired(), Length(max=7)], default='#48bb78')


class ShareTaskForm(FlaskForm):
    """Форма для предоставления доступа к задаче"""
    email = StringField('Email пользователя', validators=[DataRequired(), Email()])
    permission = SelectField('Права доступа',
                            choices=[('view', 'Только просмотр'), ('edit', 'Редактирование')],
                            default='view')