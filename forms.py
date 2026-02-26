from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, DateField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

class LoginForm(FlaskForm):
    """Форма для входа пользователя"""
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember = BooleanField('Запомнить меня')

class RegistrationForm(FlaskForm):
    """Форма для регистрации нового пользователя"""
    username = StringField('Имя пользователя',
                          validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email',
                       validators=[DataRequired(), Email()])
    password = PasswordField('Пароль',
                            validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Повторите пароль',
                             validators=[DataRequired(), EqualTo('password')])

class TaskForm(FlaskForm):
    """Форма для создания и редактирования задачи"""
    title = StringField('Название задачи',
                       validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Описание',
                               validators=[Optional(), Length(max=500)])
    due_date = DateField('Дата выполнения',
                        format='%Y-%m-%d',
                        validators=[DataRequired()])