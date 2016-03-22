import logging

from scrapy.exceptions import IgnoreRequest, NotConfigured

from ..dupe_predict import DupePredictor
from ..utils import extract_text


logger = logging.getLogger(__name__)


class AvoidDupContentMiddleware:
    '''
    Avoid requests for duplicate content. During crawling this middleware
    learns what parameters are important (influence content), and what can
    be safely ignored. Once it is confident it can start dropping
    (or de-prioritizing) requests that are unlikely to get new content.

    Required settings:
    AVOID_DUP_CONTENT_ENABLED = True
    '''
    def __init__(self):
        self.dupe_predictor = DupePredictor()

    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.settings.getbool('AVOID_DUP_CONTENT_ENABLED'):
            raise NotConfigured
        return cls()

    def process_request(self, request, spider):
        dupe_prob = self.dupe_predictor.dupe_prob(request.url)
        # TODO - lower priority for some requests
        if dupe_prob > 0.98:
            logger.debug('Ignoring a likely duplicate %s with prob %3.f',
                         request.url, dupe_prob)
            raise IgnoreRequest

    def process_response(self, request, response, spider):
        self.dupe_predictor.update_model(
            url=response.url, text=extract_text(response))
        return response
