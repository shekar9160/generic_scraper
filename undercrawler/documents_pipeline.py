import logging
import os.path
from urllib.parse import urlsplit

from scrapy import Request
from scrapy.pipelines.files import FilesPipeline, S3FilesStore, FSFilesStore
from scrapy.exceptions import DropItem
from scrapy_splash import SplashRequest, SlotPolicy

from .utils import load_directive


logging.getLogger('botocore').setLevel(logging.WARNING)


class CDRDocumentsPipeline(FilesPipeline):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lua_source = load_directive('download.lua')
        self._checksums = set()

    def get_media_requests(self, item, info):
        url = item.get('obj_original_url')
        if url:
            kwargs = dict(
                url=url,
                priority=-2,
                meta={
                    'download_slot':
                        '{} documents'.format(urlsplit(url).netloc),
                },
            )
            if self.crawler.settings.getbool('USE_SPLASH'):
                request = SplashRequest(
                    endpoint='execute',
                    args={'lua_source': self.lua_source},
                    slot_policy=SlotPolicy.SCRAPY_DEFAULT,
                    **kwargs)
            else:
                request = Request(**kwargs)
            return [request]
        else:
            return []

    def media_to_download(self, request, info):
        return None  # always download to get correct content_type

    def item_completed(self, results, item, info):
        if item.get('obj_original_url'):
            if len(results) == 1:
                [(ok, meta)] = results
                if ok and meta['checksum'] not in self._checksums:
                    self._checksums.add(meta['checksum'])
                    item['content_type'] = meta['content_type']
                    if isinstance(self.store, S3FilesStore):
                        item['obj_stored_url'] = 's3://{}/{}{}'.format(
                            self.store.bucket, self.store.prefix, meta['path'])
                    elif isinstance(self.store, FSFilesStore):
                        item['obj_stored_url'] = os.path.join(
                            self.store.basedir, meta['path'])
                    return item
            raise DropItem
        return item

    def media_downloaded(self, response, request, info):
        result = super().media_downloaded(response, request, info)
        result['content_type'] = response.headers.get(b'content-type', b'')\
                                 .decode('ascii', 'ignore')
        return result
