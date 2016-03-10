from http.cookies import SimpleCookie
from urllib.parse import urljoin
import json
import logging

import requests
from scrapy.exceptions import IgnoreRequest


logger = logging.getLogger(__name__)


class AutologinMiddleware:
    '''
    Autologin middleware uses autologin to make all requests while being
    logged in. It uses autologin to get cookies, detects logouts and tries
    to avoid them in the future.
    This middleware should be placed before the CookiesMiddleware, so that
    is "sees" the cookies in responses.

    We assume a single domain in the whole process here.
    To relax this assumption, following fixes are required:
    - make all state in AutologinMiddleware be domain dependant
    - do not block event loop in login() method (instead, collect
    scheduled requests in a separate queue and make request with scrapy).
    '''
    def __init__(self, autologin_url):
        self.autologin_url = autologin_url
        self.logged_in = False
        self.logout_urls = set()
        self.auth_cookies = dict()
        self.infly_requests = set()
        self.retry_requests = dict()

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings.get('AUTOLOGIN_URL'))

    def process_request(self, request, spider):
        ''' Login if we are not logged in yet.
        '''
        # TODO - splash
        if not self.logged_in:
            self.auth_cookies = self.get_cookies(request.url)
            self.logged_in = True
        elif request.url in self.logout_urls:
            logger.debug('Ignoring logout request %s', request.url)
            raise IgnoreRequest
        # Do our own "cookie" management, so that changes in self.auth_cookies
        # are applied to all future requests immediately.
        if self.auth_cookies:
            request.headers.pop('cookie', None)
            request.headers['cookie'] = '; '.join(
                '{}={}'.format(k, v) for k, v in self.auth_cookies.items())
            logger.debug('Sending headers %s for request %s',
                        request.headers.getlist('cookie'), request)

    def get_cookies(self, url):
        logger.debug('Attempting login at %s', url)
        r = requests.post(
            urljoin(self.autologin_url, '/login-cookies'),
            data=json.dumps({
                # FIXME
                'url': urljoin(url, '/accounts/login/'),
                'username': 'admin',
                'password': 'admin',
                }),
            headers={'content-type': 'application/json'},
            )
        cookies = r.json().get('cookies')
        if cookies:
            cookie_dict = {c['name']: c['value'] for c in cookies}
            logger.debug('Got cookies after login (%s)', cookie_dict)
            return cookie_dict

    def process_response(self, request, response, spider):
        ''' If we were logged out, login again and retry request.
        '''
        if self.is_logout(response):
            logger.debug('Logged out at %s, will retry login', response.url)
            self.auth_cookies = self.get_cookies(request.url)
            # TODO - could have been an expired session, do not judge too early
            self.logout_urls.add(response.url)
            raise IgnoreRequest
        return response

    def is_logout(self, response):
        return self.auth_cookies and any(
            name in self.auth_cookies and m.value == ''
            for name, m in get_response_cookies(response).items())


def get_response_cookies(response):
    cookies = SimpleCookie()
    for set_cookie in response.headers.getlist('set-cookie'):
        cookies.load(set_cookie.decode('utf-8'))
    return cookies
