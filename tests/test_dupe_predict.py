import logging

import pytest

from undercrawler.dupe_predict import DupePredictor


logging.basicConfig(level=logging.DEBUG)


@pytest.mark.parametrize('reverse_update', [True, False])
@pytest.mark.parametrize('reverse_test', [True, False])
@pytest.mark.parametrize('is_param', [True, False])
def test_1(reverse_update, reverse_test, is_param):
    dupe_predictor = DupePredictor()
    def gen_urls(page):
        tpls = ['{}/?page={}', '{}/?page={}&start=0'] if is_param else \
               ['{}/{}',       '{}/{}?start=0']
        return [tpl.format('http://foo.com', page) for tpl in tpls]
    for i in range(100):
        urls = gen_urls(i)
        if reverse_update:
            urls.reverse()
        for url in urls:
            dupe_predictor.update_model(url, 'a{}'.format(i))
    dupe_predictor.log_dupstats(min_dup=1)
    url1, url2 = gen_urls('b')
    if reverse_test:
        url1, url2 = url2, url1
    dupe_predictor.update_model(url1, 'b')
    assert dupe_predictor.get_dupe_prob(url2) > 0.97
    for url in gen_urls('c'):
        assert dupe_predictor.get_dupe_prob(url) < 0.1
