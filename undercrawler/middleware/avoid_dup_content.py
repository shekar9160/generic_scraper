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
        self.dupe_predictor = None
        # We initialize dupe detector only after gathering enough pages,
        # it needs them for better duplicate detection, to know which content
        # is common to a lot of pages, and which is unique.
        self.initial_queue = []  # (url, text)
        self.initial_queue_limit = 300

    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.settings.getbool('AVOID_DUP_CONTENT_ENABLED'):
            raise NotConfigured
        return cls()

    def process_request(self, request, spider):
        if self.dupe_predictor:
            dupe_prob = self.dupe_predictor.get_dupe_prob(request.url)
            # TODO - lower priority for some requests
            if dupe_prob > 0.98:
                logger.debug('Ignoring a likely duplicate %s with prob %3.f',
                            request.url, dupe_prob)
                raise IgnoreRequest

    def process_response(self, request, response, spider):
        url, text = response.url, extract_text(response)
        if self.dupe_predictor:
            self.dupe_predictor.update_model(url, text)
        else:
            self.initial_queue.append((url, text))
            if len(self.initial_queue) >= self.initial_queue_limit:
                logger.debug(
                    'Gathered enough intitial pages, building DupePredictor')
                self.dupe_predictor = DupePredictor(
                    texts_sample=[text for _, text in self.initial_queue])
                # Update model with all the pages we have missed
                for url, text in self.initial_queue:
                    self.dupe_predictor.update_model(url, text)
                self.initial_queue = None
        return response
