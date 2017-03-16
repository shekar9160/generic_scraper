from urllib.parse import urlsplit

from scrapy import Request
from scrapy_splash import SplashRequest, SlotPolicy
from scrapy_cdr.media_pipeline import CDRMediaPipeline

from .utils import load_directive, using_splash


class UndercrawlerMediaPipeline(CDRMediaPipeline):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lua_source = load_directive('download.lua')

    def media_request(self, url):
        kwargs = dict(
            url=url,
            priority=-2,
            meta={'download_slot': (
                '{} documents'.format(urlsplit(url).netloc)),
            },
        )
        if using_splash(self.crawler.settings):
            return SplashRequest(
                endpoint='execute',
                args={'lua_source': self.lua_source},
                slot_policy=SlotPolicy.SCRAPY_DEFAULT,
                **kwargs)
        else:
            return Request(**kwargs)
