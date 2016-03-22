import logging

from undercrawler.dupe_predict import DupePredictor


logging.basicConfig(level=logging.DEBUG)


def test_1():
    def make_dp():
        dupe_predictor = DupePredictor()
        url = dupe_predictor.update_model
        for _ in range(100):
            url('http://foo.com/a?start=0', 'a')
        for _ in range(100):
            url('http://foo.com/a', 'a')
        return dupe_predictor
    dupe_predictor = make_dp()
    dupe_predictor.update_model('http://foo.com/b', 'b')
    assert dupe_predictor.get_dupe_prob('http://foo.com/b?start=0') > 0.97
    # Different order of urls for b: first full, then incomplete
    dupe_predictor = make_dp()
    dupe_predictor.update_model('http://foo.com/b?start=0', 'b')
    assert dupe_predictor.get_dupe_prob('http://foo.com/b') > 0.97
