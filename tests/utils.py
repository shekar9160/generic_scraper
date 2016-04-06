class CollectorPipeline:
    def process_item(self, item, spider):
        if not hasattr('spider', 'collected_items'):
            spider.collected_items = []
        spider.collected_items.append(item)
        return item
