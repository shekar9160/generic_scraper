from scrapyjs.utils import dict_hash
from scrapy.dupefilters import RFPDupeFilter
from scrapy.utils.request import request_fingerprint


class HHSplashAwareDupefilter(RFPDupeFilter):
    ''' This is similar to SplashAwareDupeFilter, but only takes
    url, method and body into account, not headers or other stuff.

    Headers are not taken in account because of autologin:
    we don't want to restart the crawl when we get a new set of cookies
    after "login -> logout -> login again".
    '''
    def request_fingerprint(self, request):
        fp = request_fingerprint(request, include_headers=False)
        if 'splash' not in request.meta:
            return fp
        hash_keys = {'url', 'body', 'http_method'}
        to_hash = {k: v for k, v in request.meta['splash']['args'].items()
                   if k in hash_keys}
        return dict_hash(to_hash, fp)
