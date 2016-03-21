#!/usr/bin/env python
import argparse, os
from collections import namedtuple, defaultdict, Counter
from urllib.parse import urlsplit, parse_qs, urlencode

from datasketch import LSH

from scripts.utils import item_reader, get_too_common_shingles, get_min_hash


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('crawler_out')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument(
        '--action', choices=['analyze_file', 'learn_duplicates'],
        default='analyze_file')
    args = parser.parse_args()
    fn = globals()[args.action]

    print('site'.ljust(40), '\t'.join(['urls', 'set(u)', 'pth', 'uniq']))
    if os.path.isdir(args.crawler_out):
        for filename in os.listdir(args.crawler_out):
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
        min_hash = get_min_hash(item, too_common)
        key = 'item_{}'.format(i)
        item = {'url': item['url']}
        documents[key] = Doc(item, min_hash)
        lsh.insert(key, min_hash)
    paths = [''.join([p.netloc, p.path]) for p in map(urlsplit, urls)]
    duplicates = get_duplicates(lsh, documents, verbose=verbose)
    # TODO - now learn what parameters are important and what are not
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

    threshold = 0.9
    lsh = LSH(threshold=threshold, num_perm=128)
    too_common = get_too_common_shingles(f, name, limit=300)

    crawled_urls = {}  # url: min_hash
    urls_by_path = defaultdict(list)  # path: [(url, query)]

    # Duplicate hypotheses                            # Key:
    # All items with same path are duplicates         #
    path_dupstats = defaultdict(DupStat)              # path
    # All items with same path that differ only in given param are duplicates
    param_dupstats = defaultdict(DupStat)             # param
    # Same but conditioned by path                    #
    path_param_dupstats = defaultdict(DupStat)        # (path, param)
    # All items with same path with only added param=value are duplicates
    param_value_dupstats = defaultdict(DupStat)       # (param, value)
    # Same but conditioned by path                    #
    path_param_value_dupstats = defaultdict(DupStat)  # (path, param, value)

    for i, item in enumerate(item_reader(f, name)):
        min_hash = get_min_hash(item, too_common)
        item_path, item_query = parse_url(item['url'])
        item_url = unparse_url(item_path, item_query)
        duplicates = [(url, parsed) for url, parsed in (
            (url, parse_url(url)) for url in lsh.query(min_hash))
            if parsed.path == item_path]

        _update_dupstats = lambda ds, fn=None: update_dupstats(
            ds, duplicates, urls_by_path, item_path, fn=fn)
        _update_dupstats(path_dupstats[item_path])

        for param, value in item_query.items():
            item_q_without_param = _without_key(item_query, param)
            for ds in [param_dupstats[param],
                       path_param_dupstats[item_path, param]]:
                _update_dupstats(
                    ds, lambda q: (
                        item_q_without_param == _without_key(q, param)
                        and q.get(param) != value))
            for ds in [param_value_dupstats[param, value],
                       path_param_value_dupstats[item_path, param, value]]:
                _update_dupstats(ds, lambda q: item_q_without_param == q)

        if i % 100 == 0:
            for ds, name in [
                    (path_dupstats, 'Path dupstats'),
                    (param_dupstats, 'Param dupstats'),
                    (path_param_dupstats, 'Path-param dupstats'),
                    (param_value_dupstats, 'Param-value dupstats'),
                    (path_param_value_dupstats, 'Path-param-value dupstats'),
                    ]:
                print_dupstats(ds, name)

        lsh.insert(item_url, min_hash)
        crawled_urls[item_url] = min_hash
        urls_by_path[item_path].append((item_url, item_query))


def _without_key(dict_, key):
    return {k: v for k, v in dict_.items() if k != key}


def update_dupstats(dupstat, duplicates, urls_by_path, item_path, fn=None):
    fn = fn or (lambda q: True)
    duplicates = {url for url, (path, query) in duplicates if fn(query)}
    dupstat.dup += len(duplicates)
    dupstat.nodup += len(
        {url for url, query in urls_by_path[item_path] if fn(query)}
        .difference(duplicates))


def print_dupstats(dupstats, name):
    dupstats_items = [
        (url, dupstat) for url, dupstat in sorted(
            dupstats.items(), key=lambda x: x[1].total, reverse=True)
        if dupstat.dup > 2]
    if dupstats_items:
        print('\n{}:'.format(name))
        for url, dupstat in dupstats_items:
            print(url, dupstat)


class DupStat:
    def __init__(self):
        self.dup = 0
        self.nodup = 0

    @property
    def total(self):
        return self.dup + self.nodup

    def __repr__(self):
        return '<DupStat: ({}, {})>'.format(self.dup, self.nodup)


URL = namedtuple('URL', ['path', 'query'])


def parse_url(url):
    p = urlsplit(url)
    # TODO - multiple values
    query = {k: v[0] for k, v in parse_qs(p.query).items()}
    return URL(''.join([p.netloc, p.path]), query)


def unparse_url(path, query):
    return '?'.join([path, urlencode(sorted(query.items()))])


if __name__ == '__main__':
    main()
