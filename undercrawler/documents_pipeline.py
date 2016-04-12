import logging
import os.path

from scrapy.http import Request
from scrapy.pipelines.files import FilesPipeline, S3FilesStore, FSFilesStore
from scrapy.exceptions import DropItem


logging.getLogger('botocore').setLevel(logging.WARNING)


class CDRDocumentsPipeline(FilesPipeline):
    def get_media_requests(self, item, info):
        url = item.get('obj_original_url')
        return [Request(url)] if url else []

    def item_completed(self, results, item, info):
        if item.get('obj_original_url'):
            if len(results) == 1:
                [(ok, meta)] = results
                if ok:
                    if isinstance(self.store, S3FilesStore):
                        item['obj_stored_url'] = 's3://{}/{}{}'.format(
                            self.store.bucket, self.store.prefix, meta['path'])
                    elif isinstance(self.store, FSFilesStore):
                        item['obj_stored_url'] = os.path.join(
                            self.store.basedir, meta['path'])
                    return item
            raise DropItem
        return item
