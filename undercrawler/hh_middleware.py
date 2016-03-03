import json

from scrapy.http import Response
from scrapy.http.cookies import CookieJar
from scrapyjs.middleware import SplashMiddleware


class HHMiddleware(SplashMiddleware):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.jar = CookieJar()

    def process_request(self, request, spider):
        if request.meta.get('_splash_processed'):
            return
        splash_options = request.meta.get('splash')
        self._set_request_cookies(self.jar, request)
        if splash_options:
            args = splash_options.get('args', {})
            args.update({
                'method': request.method,
                'body': request.body.decode('utf-8') or None,
                'headers': request.headers.to_unicode_dict(),
                })
            args['headers']['xcustom'] = 'yess'
            splash_options['args'] = {
                k: v for k, v in args.items() if v is not None}
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
            # TODO - more subte than request.replace!!!
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
