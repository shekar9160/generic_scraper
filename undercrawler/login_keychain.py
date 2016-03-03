from collections import namedtuple


Credentials = namedtuple('Credentials', ['login', 'password'])


def get_credentials(_url):
    return Credentials('admin', 'admin')
