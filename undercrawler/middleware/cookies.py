from autologin_middleware import ExposeCookiesMiddleware
from scrapy.exceptions import NotConfigured


class CookiesMiddlewareIfNoSplash(ExposeCookiesMiddleware):
    @classmethod
    def from_crawler(cls, crawler):
        if crawler.settings.get('SPLASH_URL'):
            raise NotConfigured
        return super().from_crawler(crawler)
