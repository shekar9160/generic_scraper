import re
from copy import deepcopy

from scrapy_splash import SplashAwareDupeFilter


class DupeFilter(SplashAwareDupeFilter):
    """
    Consider same urls with and without www and using http or https
    as duplicates.
    """
    def request_fingerprint(self, request):
        # It's only valid to do this normalization when using splash, which
        # handles redirects "inside" splash. If scrapy sees these redirects,
        # then http -> https and non-www -> www redirects will be dropped.
        if 'splash' in request.meta and \
                not request.meta.get('_splash_processed'):
            url = re.sub(r'^https?://(www\.)?', 'http://', request.url)
            meta = deepcopy(request.meta)
            meta['splash'].setdefault('args', {})['url'] = url
            request = request.replace(url=url, meta=meta)
        return super().request_fingerprint(request)
