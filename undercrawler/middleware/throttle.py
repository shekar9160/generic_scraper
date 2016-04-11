from scrapy.extensions.throttle import AutoThrottle
from scrapy.exceptions import NotConfigured
from scrapy_splash.response import SplashJsonResponse


class SplashAwareAutoThrottle(AutoThrottle):
    def __init__(self, crawler):
        self.crawler = crawler
        self.target_concurrency = \
            crawler.settings.getfloat('AUTOTHROTTLE_TARGET_CONCURRENCY')
        self.debug = crawler.settings.getbool('AUTOTHROTTLE_DEBUG')

    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.settings.getbool('SPLASH_AUTOTHROTTLE_ENABLED'):
            raise NotConfigured
        return cls(crawler)

    def process_request(self, request, spider):
        if not hasattr(spider, 'download_delay'):
            self._spider_opened(spider)

    def process_response(self, request, response, spider):
        if isinstance(response, SplashJsonResponse) and 'har' in response.data:
            pages = response.data['har']['log'].get('pages')
            if pages:
                t_ms = pages[-1].get('pageTimings', {}).get('onContentLoad')
                if t_ms is not None:
                    request.meta['download_latency'] = t_ms / 1000
        self._response_downloaded(response, request, spider)
        return response
