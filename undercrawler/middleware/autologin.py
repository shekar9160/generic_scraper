from http.cookies import SimpleCookie
from urllib.parse import urljoin
import json
import logging
import time
from copy import deepcopy

import requests
from scrapy.exceptions import IgnoreRequest, NotConfigured


logger = logging.getLogger(__name__)


class AutologinMiddleware:
    '''
    Autologin middleware uses autologin to make all requests while being
    logged in. It uses autologin to get cookies, detects logouts and tries
    to avoid them in the future.

    Required settings:
    AUTOLOGIN_ENABLED = True
    AUTOLOGIN_URL: url of where the autologin service is running
    COOKIES_ENABLED = False (this could be relaxed perhaps)

    Optional settings:
    AUTH_COOKIES: pass auth cookies after manual login (format is_logout
    "name=value; name2=value2")
    LOGOUT_URL: pass url substring to avoid
    USERNAME, PASSWORD, LOGIN_URL are passed to autologin and
    override values from stored credentials.  LOGIN_URL is a relative url.
    It can be omitted if it is the same as the start url.

    We assume a single domain in the whole process here.
    To relax this assumption, following fixes are required:
    - make all state in AutologinMiddleware be domain dependant
    - do not block event loop in login() method (instead, collect
    scheduled requests in a separate queue and make request with scrapy).
    '''
    def __init__(self, autologin_url, auth_cookies=None, logout_url=None,
                 splash_url=None, login_url=None, username=None, password=None):
        self.autologin_url = autologin_url
        self.splash_url = splash_url
        self.login_url = login_url
        self.username = username
        self.password = password
        if auth_cookies:
            cookies = SimpleCookie()
            cookies.load(auth_cookies)
            self.auth_cookies = [
                {'name': m.key, 'value': m.value} for m in cookies.values()]
            self.logged_in = True
        else:
            self.auth_cookies = None
            self.logged_in = False
        self.logout_urls = set()
        if logout_url:
            self.logout_urls.add(logout_url)

    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.settings.getbool('AUTOLOGIN_ENABLED'):
            raise NotConfigured
        return cls(**{name.lower(): crawler.settings.get(name) for name in [
            'AUTOLOGIN_URL', 'AUTH_COOKIES', 'LOGOUT_URL', 'SPLASH_URL',
            'LOGIN_URL', 'USERNAME', 'PASSWORD']})

    def process_request(self, request, spider):
        ''' Login if we are not logged in yet.
        '''
        if '_autologin' in request.meta:
            return
        # Save original request to be able to retry it in case of logout
        req_copy = request.replace(meta=deepcopy(request.meta))
        req_copy.callback = req_copy.errback = None
        request.meta['_autologin'] = autologin_meta = {'request': req_copy}

        if not self.logged_in:
            self.auth_cookies = self.get_auth_cookies(request.url)
            self.logged_in = True
        elif any(url in request.url for url in self.logout_urls):
            logger.debug('Ignoring logout request %s', request.url)
            raise IgnoreRequest

        # Always apply self.cookies, so that changes in self.auth_cookies
        # are applied to all future requests immediately.
        if self.auth_cookies:
            request.cookies = self.auth_cookies
            autologin_meta['cookie_dict'] = {
                c['name']: c['value'] for c in self.auth_cookies}

    def get_auth_cookies(self, url):
        logger.debug('Attempting login at %s', url)
        while True:
            request = requests.post(
                urljoin(self.autologin_url, '/login-cookies'),
                data=json.dumps({
                    'url': urljoin(url, self.login_url) if self.login_url else
                           url,
                    'username': self.username,
                    'password': self.password,
                    'splash_url': self.splash_url,
                }),
                headers={'content-type': 'application/json'})
            response = request.json()
            status = response['status']
            logger.debug('Got login response with status "%s"', status)
            if status == 'pending':
                time.sleep(1.0)
                continue
            elif status == 'skipped':
                return None
            elif status == 'solved':
                cookies = response.get('cookies')
                if cookies:
                    cookies = _cookies_to_har(cookies)
                    logger.debug('Got cookies after login %s', cookies)
                    return cookies
                else:
                    logger.debug('No cookies after login')
                    return None

    def process_response(self, request, response, spider):
        ''' If we were logged out, login again and retry request.
        '''
        logger.debug('response %s cookies %s', response, response.cookiejar)
        if self.is_logout(response):
            logger.debug('Logout at %s %s',
                         response.url, response.cookiejar)
            autologin_meta = request.meta['_autologin']
            # We could have already done relogin after initial logout
            if any(autologin_meta['cookie_dict'].get(c['name']) != c['value']
                    for c in self.auth_cookies):
                retryreq = autologin_meta['request'].copy()
                retryreq.dont_filter = True
                logger.debug('Stale request %s was logged out, will retry %s',
                             response, retryreq)
                return retryreq
            logger.debug('Logged out at %s, will retry login', response.url)
            self.auth_cookies = self.get_auth_cookies(response.url)
            # TODO - could have been an expired session, do not judge too early
            self.logout_urls.add(response.url)
            raise IgnoreRequest
        return response

    def is_logout(self, response):
        auth_cookies = {c['name'] for c in self.auth_cookies if c['value']}
        response_cookies = {m.name for m in response.cookiejar if m.value}
        return bool(auth_cookies - response_cookies)


def _cookies_to_har(cookies):
    # Leave only documented cookie attributes
    return [{
        'name': c['name'],
        'value': c['value'],
        'path': c.get('path', '/'),
        'domain': c.get('domain', ''),
        } for c in cookies]
