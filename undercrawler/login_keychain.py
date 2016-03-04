from collections import namedtuple


Credentials = namedtuple('Credentials', ['login', 'password'])


def get_credentials(_url):
    return Credentials('admin', 'admin')


def add_registration_task(_url):
    print('added registration task')
