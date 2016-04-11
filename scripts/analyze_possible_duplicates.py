#!/usr/bin/env python
import argparse, logging, os
from collections import namedtuple
from urllib.parse import urlsplit

from datasketch import LSH
from scrapy.utils.url import canonicalize_url

from undercrawler.utils import get_min_hash
from undercrawler.dupe_predict import DupePredictor, _parse_url
from scripts.utils import item_reader, get_too_common_shingles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('crawler_out')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument(
        '--action', choices=['analyze_file', 'learn_duplicates'],
        default='analyze_file')
    args = parser.parse_args()
    fn = globals()[args.action]

    if args.action == 'analyze_file':
        print('site'.ljust(40), '\t'.join(['urls', 'set(u)', 'pth', 'uniq']))
    if os.path.isdir(args.crawler_out):
        for filename in os.listdir(args.crawler_out):
            if any(filename.endswith(ext) for ext in ['.json', '.jl']):
                with open(os.path.join(args.crawler_out, filename)) as f:
                    fn(filename, f, verbose=args.verbose)
    else:
        with open(args.crawler_out) as f:
            fn(os.path.basename(args.crawler_out), f, verbose=args.verbose)


def analyze_file(name, f, verbose=False):
    urls = []
    Doc = namedtuple('Doc', ['item', 'min_hash'])
    documents = {} # key -> Doc
    lsh = LSH(threshold=0.9, num_perm=128)
    too_common = get_too_common_shingles(f, name, limit=300)
    for i, item in enumerate(item_reader(f, name)):
        urls.append(item['url'])
        min_hash = get_min_hash(item['extracted_text'], too_common)
        key = 'item_{}'.format(i)
        item = {'url': item['url']}
        documents[key] = Doc(item, min_hash)
        lsh.insert(key, min_hash)
    paths = [''.join([p.netloc, p.path]) for p in map(urlsplit, urls)]
    duplicates = get_duplicates(lsh, documents, verbose=verbose)
    print(name.ljust(40), '\t'.join(map(str, [
        len(urls), len(set(urls)), len(set(paths)),
        n_unique(documents, duplicates),
        ])))


def get_duplicates(lsh, documents, verbose=False):
    duplicates = {}
    for key, (item, min_hash) in documents.items():
        dupe_keys = set(lsh.query(min_hash))
        if key in dupe_keys:
            dupe_keys.remove(key)
        if dupe_keys:
            duplicates[key] = dupe_keys
            if verbose:
                print()
                print(item['url'])
                for k in dupe_keys:
                    print(documents[k].item['url'])
    return duplicates


def n_unique(documents, duplicates):
    unique = set()
    for key in documents:
        if key not in duplicates or \
                not any(k in unique for k in duplicates[key]):
            unique.add(key)
    return len(unique)


def learn_duplicates(name, f, verbose=False):
    print(name)
    logging.basicConfig(level=logging.DEBUG)
    texts_sample = [
        item['extracted_text'] for item in item_reader(f, name, limit=300)]
    dupe_predictor = DupePredictor(texts_sample)

    lsh = LSH(threshold=0.9, num_perm=128)  # separate from dupe_predictor
    too_common_shingles = dupe_predictor.too_common_shingles
    threshold = 0.98
    y_pred, y_true = [], []
    def _report_pr():
        tp = sum(p > threshold and d for p, d in zip(y_pred, y_true))
        fp = sum(p > threshold and not d for p, d in zip(y_pred, y_true))
        fn = sum(p < threshold and d for p, d in zip(y_pred, y_true))
        n_dup = tp + fn
        print('precision: %.3f, recall %.3f at %.2f threshold '
                '(%d duplicates)' % (
            tp / (tp + fp) if tp else 0.,
            tp / n_dup if n_dup else 0., threshold, n_dup))
    for i, item in enumerate(item_reader(f, name)):
        dupe_prob = dupe_predictor.get_dupe_prob(item['url'])
        y_pred.append(dupe_prob)
        min_hash = get_min_hash(item['extracted_text'], too_common_shingles)
        if dupe_prob < threshold:
            duplicates = [url for url, _ in dupe_predictor.update_model(
                item['url'], item['extracted_text'])]
        else:
            # We think this is a duplicate: replicate crawling
            # and do not update the model.
            duplicates = list(lsh.query(min_hash))
        lsh.insert(canonicalize_url(item['url']), min_hash)
        y_true.append(bool(duplicates))
        if verbose:
            if duplicates and dupe_prob < threshold:
                path, _ = _parse_url(item['url'])
                sample = [url for url in duplicates
                          if _parse_url(url)[0] == path] or duplicates
                print('false negative %s (%s, %d more)' % (
                    item['url'], sample[0], len(sample) - 1))
            elif not duplicates and dupe_prob > threshold:
                print('false positive', item['url'])
        if i % 100 == 0:
            _report_pr()
    _report_pr()


if __name__ == '__main__':
    main()
