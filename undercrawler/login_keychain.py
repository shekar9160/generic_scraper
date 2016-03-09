from collections import namedtuple

from .login_keychain_ui import KeychainItem


Credentials = namedtuple('Credentials', ['login', 'password'])


def get_credentials(url):
    return [Credentials(login, password)
            for login, password in KeychainItem.solved_by_login_url(url)]


def add_registration_task(url, max_per_domain):
    KeychainItem.add_task(url, max_per_domain)


def any_unsolved():
    return KeychainItem.any_unsolved()
