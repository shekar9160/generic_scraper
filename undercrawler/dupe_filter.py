import re
from copy import deepcopy

from scrapy_splash import SplashAwareDupeFilter


class DupeFilter(SplashAwareDupeFilter):
    """
    Consider same urls with and without www as duplicates.
    """
    def request_fingerprint(self, request):
        if not request.meta.get('_splash_processed'):
            url = re.sub(r'^https?://(www\.)?', 'http://', request.url)
            kwargs = {'url': url}
            if 'splash' in request.meta:
                kwargs['meta'] = deepcopy(request.meta)
                kwargs['meta']['splash'].setdefault('args', {})['url'] = url
            request = request.replace(**kwargs)
        return super().request_fingerprint(request)
