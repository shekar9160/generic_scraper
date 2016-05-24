import os

import pytest
from scrapy.settings import Settings
from scrapy.crawler import CrawlerRunner

import undercrawler.settings
from undercrawler.spiders import BaseSpider


pytest_plugins = 'pytest_twisted'


@pytest.fixture(params=[False, True])
def settings(request):
    use_splash = request.param
    s = Settings()
    s.setmodule(undercrawler.settings)
    s.update({
        'DOWNLOAD_DELAY': 0.01,
        'AUTOTHROTTLE_START_DELAY': 0.01,
        'RUN_HH': False,
        'USE_SPLASH': use_splash,
        })
    s['ITEM_PIPELINES']['tests.utils.CollectorPipeline'] = 100
    splash_url = os.environ.get('SPLASH_URL')
    if splash_url:
        s['SPLASH_URL'] = splash_url
    return s


def make_crawler(settings, **extra_settings):
    settings.update(extra_settings)
    runner = CrawlerRunner(settings)
    return runner.create_crawler(BaseSpider)
