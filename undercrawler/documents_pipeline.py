import logging
import os.path
from urllib.parse import urlsplit

from scrapy.http import Request
from scrapy.pipelines.files import FilesPipeline, S3FilesStore, FSFilesStore
from scrapy.exceptions import DropItem


logging.getLogger('botocore').setLevel(logging.WARNING)


class CDRDocumentsPipeline(FilesPipeline):
    def get_media_requests(self, item, info):
        url = item.get('obj_original_url')
        if url:
            return [Request(url, meta={
                'download_slot': '{} documents'.format(urlsplit(url).netloc),
                'skip_avoid_dup_content': True,
                })]
        else:
            return []

    def item_completed(self, results, item, info):
        if item.get('obj_original_url'):
            if len(results) == 1:
                [(ok, meta)] = results
                if ok:
                    if meta['content_type']:
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
