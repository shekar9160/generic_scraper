import json
import os.path

from scrapy.http import Headers
from scrapy.downloadermiddlewares.cookies import CookiesMiddleware
from scrapyjs.middleware import SplashMiddleware


class HHSplashMiddleware(SplashMiddleware, CookiesMiddleware):
    ''' Middleware that extends SplashMiddleware from scrapyjs:
    * Make all requests using headless_horseman.lua, including POST requests.
    * Add cookies support.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        CookiesMiddleware.__init__(self)
        # Load headless_horseman scripts
        root = os.path.join(os.path.dirname(__file__), '../directives')
        with open(os.path.join(root, 'headless_horseman.lua')) as f:
            self.lua_source = f.read()
        with open(os.path.join(root, 'headless_horseman.js')) as f:
            self.js_source = f.read()

    def process_request(self, request, spider):
        if request.meta.get('_splash_processed'):
            return
        CookiesMiddleware.process_request(self, request, spider)
        request.meta['splash'] = {
            'endpoint': 'execute',
            'args': _without_None({
                'force_splash': True,
                'lua_source': self.lua_source,
                'js_source': self.js_source,
                'run_hh': self.crawler.settings.getbool('RUN_HH'),
                'return_png': False,
                'method': request.method,
                'body': request.body.decode('utf-8') or None,
                'headers': request.headers.to_unicode_dict(),
            })
        }
        return super().process_request(request, spider)

    def process_response(self, request, response, spider):
        response = super().process_response(request, response, spider)
        data = json.loads(response.text)
        if 'url' in data:
            headers = Headers()
            # FIXME - this collects headers from all requests,
            # so is not quite correct. We are interested in cookies, so we
            # could instead get them, but splash:get_cookies() returns
            # them in a different format.
            for entry in data['har']['log']['entries']:
                for h in entry['response']['headers']:
                    current_headers = set(headers.getlist(h['name']))
                    # FIXME - this splitting looks like a splash bug?
                    for v in h['value'].split('\n'):
                        if v not in current_headers:
                            headers.appendlist(h['name'], v)
            response = response.replace(
                url=data['url'],
                headers=headers,
                body=data['html'].encode('utf-8'))
        if not request.meta.get('dont_merge_cookies', False):
            # Replace url in request so that it matches original url
            CookiesMiddleware.process_response(
                self, request.replace(url=response.url), response, spider)
        return response


def _without_None(d):
    return {k: v for k, v in d.items() if v is not None}
