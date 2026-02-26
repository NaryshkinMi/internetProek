from datetime import datetime

def to_date(value):
    """Конвертирует datetime в date"""
    if value is None:
        return None
    if hasattr(value, 'date'):
        return value.date()
    return value

def init_filters(app):
    """Инициализация пользовательских фильтров для Jinja2"""
    app.jinja_env.filters['to_date'] = to_date