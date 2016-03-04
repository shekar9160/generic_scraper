from collections import namedtuple

from .login_keychain_ui import KeychainItem


Credentials = namedtuple('Credentials', ['login', 'password'])


def get_credentials(url):
    item = KeychainItem.get_solved_by_login_url(url)
    if item:
        login, password = item
        return Credentials(login, password)


def add_registration_task(url):
    KeychainItem.add_task(url)
