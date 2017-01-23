import tempfile

from PIL import Image
import pytest
from twisted.web.resource import Resource

from undercrawler.utils import using_splash
from .utils import text_resource, html, paths_set, find_item, inlineCallbacks
from .mockserver import MockServer
from .conftest import make_crawler


class SinglePage(text_resource(html('<b>hello</b>'))):
    pass


@inlineCallbacks
def test_single(settings):
    crawler = make_crawler(settings, AUTOLOGIN_ENABLED=False)
    with MockServer(SinglePage) as s:
        root_url = s.root_url
        yield crawler.crawl(url=root_url)
    spider = crawler.spider
    assert hasattr(spider, 'collected_items')
    assert len(spider.collected_items) == 1
    item = spider.collected_items[0]
    assert item['url'].rstrip('/') == root_url
    assert item['extracted_text'] == 'hello'
    assert item['raw_content'] == html('<b>hello</b>')


class Follow(Resource):
    def __init__(self):
        super().__init__()
        self.putChild(b'', text_resource(
            html('<a href="/one">one</a> | <a href="/two">Logout</a>'))())
        self.putChild(b'one', text_resource(html('one'))())
        self.putChild(b'two', text_resource(html('two'))())


@inlineCallbacks
def test_follow(settings, **extra):
    crawler = make_crawler(
        settings, **(extra or dict(AUTOLOGIN_ENABLED=False)))
    with MockServer(Follow) as s:
        root_url = s.root_url
        yield crawler.crawl(url=root_url)
    spider = crawler.spider
    assert hasattr(spider, 'collected_items')
    assert len(spider.collected_items) == 3
    spider.collected_items.sort(key=lambda item: item['url'])
    item0 = spider.collected_items[0]
    assert item0['url'].rstrip('/') == root_url
    item1 = spider.collected_items[1]
    assert item1['url'] == root_url + '/one'
    assert item1['raw_content'] == html('one')
    item2 = spider.collected_items[2]
    assert item2['url'] == root_url + '/two'
    assert item2['raw_content'] == html('two')


class HHPage(text_resource(html(
        '<a onclick="document.body.innerHTML=\'changed\';">more</a>'
        '<b>hello</b>'
        ))):
    pass


@inlineCallbacks
def test_hh(settings):
    crawler = make_crawler(settings, AUTOLOGIN_ENABLED=False, RUN_HH=True)
    if not using_splash(crawler.settings):
        pytest.skip('requires splash')
    with MockServer(HHPage) as s:
        root_url = s.root_url
        yield crawler.crawl(url=root_url)
    spider = crawler.spider
    assert hasattr(spider, 'collected_items')
    assert len(spider.collected_items) == 1
    item = spider.collected_items[0]
    assert item['url'].rstrip('/') == root_url
    assert item['extracted_text'] == 'changed'


FILE_CONTENTS = 'ёюя'.encode('cp1251')


class PDFFile(Resource):
    isLeaf = True
    def render_GET(self, request):
        request.setHeader(b'content-type', b'application/pdf')
        return FILE_CONTENTS


class WithFile(Resource):
    def __init__(self):
        super().__init__()
        self.putChild(b'', text_resource(html(
            '<a href="/file.pdf">file</a> '
            '<a href="/page?b=2&a=1">page</a> '
            '<a href="/forbidden.pdf">forbidden file</a>'
            ))())
        self.putChild(b'file.pdf', PDFFile())
        self.putChild(b'forbidden.pdf', text_resource(FILE_CONTENTS * 2)())
        self.putChild(b'page', text_resource(html(
            '<a href="/file.pdf">file</a>'))())


@inlineCallbacks
def test_documents(settings):
    tempdir = tempfile.TemporaryDirectory()
    crawler = make_crawler(settings, AUTOLOGIN_ENABLED=False,
                           FILES_STORE='file://' + tempdir.name)
    with MockServer(WithFile) as s:
        root_url = s.root_url
        yield crawler.crawl(url=root_url)
    spider = crawler.spider
    assert hasattr(spider, 'collected_items')
    assert len(spider.collected_items) == 4
    file_item = find_item('/file.pdf', spider.collected_items)
    assert file_item['url'] == file_item['obj_original_url'] == \
        root_url + '/file.pdf'
    with open(file_item['obj_stored_url'], 'rb') as f:
        assert f.read() == FILE_CONTENTS
    assert file_item['content_type'] == 'application/pdf'
    forbidden_item = find_item('/forbidden.pdf', spider.collected_items)
    with open(forbidden_item['obj_stored_url'], 'rb') as f:
        assert f.read() == FILE_CONTENTS * 2


class Search(Resource):
    isLeaf = True
    def render_GET(self, request):
        results = ''
        if b'query' in request.args:
            results = 'You found "{}", congrats!'\
                      .format(request.args[b'query'][0].decode())
        return html(
            '<form action="." class="search">'
            '<label for="search">Search:</label> '
            '<input id="search" name="query" type="text"/> '
            '<input type="submit" value="Search"/>'
            '</form>'
            '{}'
            ''.format(results)).encode()

    def render_POST(self, request):
        return html('You searched for "{}"'.format(request.args['query']))\
               .encode()


@inlineCallbacks
def test_crazy_form_submitter(settings):
    crawler = make_crawler(settings, AUTOLOGIN_ENABLED=False)
    with MockServer(Search) as s:
        root_url = s.root_url
        yield crawler.crawl(url=root_url, search_terms=['a', 'b'])
    spider = crawler.spider
    assert hasattr(spider, 'collected_items')
    assert len(spider.collected_items) == 3
    assert paths_set(spider.collected_items) == \
        {'/', '/?query=a', '/?query=b'}


@inlineCallbacks
def test_screenshots(settings):
    crawler = make_crawler(
        settings, AUTOLOGIN_ENABLED=False, RUN_HH=False,
        SCREENSHOT=True, SCREENSHOT_WIDTH=640, SCREENSHOT_HEIGHT=480)
    with MockServer(HHPage) as s:
        root_url = s.root_url
        yield crawler.crawl(url=root_url)
    spider = crawler.spider
    assert hasattr(spider, 'collected_items')
    if using_splash(crawler.settings):
        for item in spider.collected_items:
            screenshot_path = item['extracted_metadata']['screenshot']
            assert screenshot_path is not None
            screenshot = Image.open(screenshot_path)
            assert screenshot.size == (640, 480)


class LotsOfLinks(Resource):
    size_1 = 100
    size_2 = 10
    def __init__(self):
        super().__init__()
        self.putChild(b'', text_resource(html(
            '<br>'.join('<a href="/page{0}">Page #{0}</a>'.format(i)
                        for i in range(self.size_1))))())
        for i in range(self.size_1):
            self.putChild('page{}'.format(i).encode(), text_resource(html(
                '<br>'.join(
                    '<a href="/page{0}-{1}">Page {0} #{1}</a>'.format(i, j)
                    for j in range(self.size_2))))())


@pytest.mark.skip('This is not really a test at the moment')
@inlineCallbacks
def test_lots_of_links(settings):
    crawler = make_crawler(settings, AUTOLOGIN_ENABLED=False)
    with MockServer(LotsOfLinks) as s:
        root_url = s.root_url
        yield crawler.crawl(url=root_url)
