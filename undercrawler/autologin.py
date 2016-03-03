from urllib.parse import urlencode, urljoin


LOGIN_FIELD_TYPES = {'username', 'email', 'username or email'}
PASSWORD_FIELD_TYPES = {'password'}


def login_params(url, credentials, element, meta):
    login_field = password_field = None
    for field_name, field_type in meta['fields'].items():
        if field_type in LOGIN_FIELD_TYPES:
            login_field = field_name
        elif field_type in PASSWORD_FIELD_TYPES:
            password_field = field_name
    if login_field is not None and password_field is not None:
        element.fields[login_field] = credentials.login
        element.fields[password_field] = credentials.password
        return dict(
            url=urljoin(url, element.action) or url,
            method=element.method,
            body=urlencode(element.form_values()))
