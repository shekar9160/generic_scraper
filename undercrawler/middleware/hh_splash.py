import json
import os.path

from scrapy.http import Response
from scrapy.http.cookies import CookieJar
from scrapyjs.middleware import SplashMiddleware


class HHSplashMiddleware(SplashMiddleware):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.jar = CookieJar()
        root = os.path.join(os.path.dirname(__file__), '../directives')
        with open(os.path.join(root, 'headless_horseman.lua')) as f:
            self.lua_source = f.read()
        with open(os.path.join(root, 'headless_horseman.js')) as f:
            self.js_source = f.read()

    def process_request(self, request, spider):
        if request.meta.get('_splash_processed'):
            return
        if request.meta.get('hh_splash'):
            self._set_request_cookies(self.jar, request)
            request.meta['splash'] = {
                'endpoint': 'execute',
                'args': _without_None({
                    'force_splash': True,
                    'lua_source': self.lua_source,
                    'js_source': self.js_source,
                    'run_hh': self.crawler.settings.getbool('RUN_HH'),
                    'method': request.method,
                    'body': request.body.decode('utf-8') or None,
                    'headers': request.headers.to_unicode_dict(),
                })
            }
        return super().process_request(request, spider)

    def process_response(self, request, response, spider):
        response = super().process_response(request, response, spider)
        data = json.loads(response.text)
        if 'html' in data:
            response = response.replace(body=data['html'].encode('utf-8'))
        if 'har' in data:
            headers = {}
            for entry in data['har']['log']['entries']:
                for h in entry['response']['headers']:
                    headers[h['name']] = h['value']
            response = response.replace(headers=headers)
        if not request.meta.get('dont_merge_cookies', False):
            # FIXME - smth more subtle than request.replace?
            self.jar.extract_cookies(
                response, request.replace(url=response.url))
        return response

    # Copied from CookiesMiddleware

    def _set_request_cookies(self, jar, request):
        cookies = self._get_request_cookies(jar, request)
        for cookie in cookies:
            jar.set_cookie_if_ok(cookie, request)
        request.headers.pop('Cookie', None)
        jar.add_cookie_header(request)

    def _get_request_cookies(self, jar, request):
        if isinstance(request.cookies, dict):
            cookie_list = [
                {'name': k, 'value': v} for k, v in request.cookies.items()]
        else:
            cookie_list = request.cookies
        cookies = [self._format_cookie(x) for x in cookie_list]
        headers = {'Set-Cookie': cookies}
        response = Response(request.url, headers=headers)
        return jar.make_cookies(response, request)

    def _format_cookie(self, cookie):
        # build cookie string
        cookie_str = '%s=%s' % (cookie['name'], cookie['value'])
        if cookie.get('path', None):
            cookie_str += '; Path=%s' % cookie['path']
        if cookie.get('domain', None):
            cookie_str += '; Domain=%s' % cookie['domain']
        return cookie_str


def _without_None(d):
    return {k: v for k, v in d.items() if v is not None}
