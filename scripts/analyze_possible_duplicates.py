#!/usr/bin/env python
import argparse, os, random
from collections import namedtuple, defaultdict
from urllib.parse import urlsplit, parse_qs

from datasketch import LSH
from scrapy.utils.url import canonicalize_url

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

    if args.action == 'analyze_file':
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

    URLMeta = namedtuple('URLMeta', ['path', 'query', 'min_hash'])
    crawled_urls = {}  # url: URLMeta
    urls_by_path = defaultdict(set)  # path: {url}
    urls_by_path_q = defaultdict(set)  # (path, q): {url}
    urls_by_path_qwp = defaultdict(set)  # (path, param, q): {url}


    # Duplicate hypotheses                            # Key:
    # All items with same path are duplicates         #
    path_dupstats = defaultdict(DupStat)              # path
    # All items with same path that differ only in given param are duplicates
    param_dupstats = defaultdict(DupStat)             # param
    # Same but conditioned by path                    #
    path_param_dupstats = defaultdict(DupStat)        # (path, param)
    # Same but conditioned by path + the rest of the query
    path_query_param_dupstats = defaultdict(DupStat)  # (path, param)
    # All items with same path with only added param=value are duplicates
    param_value_dupstats = defaultdict(DupStat)       # (param, value)
    # Same but conditioned by path                    #
    path_param_value_dupstats = defaultdict(DupStat)  # (path, param, value)
    # TODO - moar power:
    # more than one get param?

    def _print_dupstats():
        for ds, name in [
                (path_dupstats, 'Path dupstats'),
                (param_dupstats, 'Param dupstats'),
                (path_param_dupstats, 'Path-param dupstats'),
                (path_query_param_dupstats, 'Path-query-param dupstats'),
                (param_value_dupstats, 'Param-value dupstats'),
                (path_param_value_dupstats, 'Path-param-value dupstats'),
                ]:
            print_dupstats(ds, name)

    def nodup_filter(min_hash, all_urls, max_sample=200):
        ''' This filters results that are considered not duplicates.
        But we really need to check that, because lsh.query does not always
        return ALL duplicates, esp. when there are a lot of them, so
        here we double-check and return only urls that are NOT duplicates.
        Return estimated number of not duplicates.
        '''
        if not all_urls:
            return 0
        urls = random.sample(all_urls, max_sample) \
               if len(all_urls) > max_sample else all_urls
        filtered = [
            url for url in urls
            if min_hash.jaccard(crawled_urls[url].min_hash) < threshold]
        return int(len(filtered) / len(urls) * len(all_urls))

    for i, item in enumerate(item_reader(f, name)):
        min_hash = get_min_hash(item, too_common)
        item_url = canonicalize_url(item['url'])
        item_path, item_query = parse_url(item_url)
        duplicates = [(url, m.query) for url, m in (
            (url, crawled_urls[url]) for url in lsh.query(min_hash))
            if m.path == item_path]

        path_nodup = nodup_filter(min_hash,
            urls_by_path[item_path].difference(url for url, _ in duplicates))
        path_dupstats[item_path].update(duplicates, path_nodup)

        for param, value in item_query.items():
            # qwp = "query without param"
            item_q_key = tuple(sorted(item_query.items()))
            item_qwp = _without_key(item_query, param)
            item_qwp_key = tuple(sorted(item_qwp.items()))

            q_dup = {url for url, q in duplicates
                     if _without_key(q, param) == item_qwp}
            q_nodup = nodup_filter(min_hash, (
                urls_by_path_qwp[item_path, param, item_qwp_key]
                .union(urls_by_path_q[item_path, item_qwp_key])
                .difference(q_dup)))
            for ds in [param_dupstats[param],
                       path_param_dupstats[item_path, param],
                       path_query_param_dupstats[item_path, param, item_qwp_key],
                       ]:
                ds.update(q_dup, q_nodup)

            qv_dup = {url for url, q in duplicates if q == item_qwp}
            qv_nodup = nodup_filter(min_hash, (
                urls_by_path_q[item_path, item_qwp_key].difference(qv_dup)))
            for ds in [param_value_dupstats[param, value],
                       path_param_value_dupstats[item_path, param, value]]:
                ds.update(qv_dup, qv_nodup)

            urls_by_path_q[item_path, item_q_key].add(item_url)
            urls_by_path_qwp[item_path, param, item_qwp_key].add(item_url)

        if verbose and i % 100 == 0:
            _print_dupstats()

        lsh.insert(item_url, min_hash)
        crawled_urls[item_url] = URLMeta(item_path, item_query, min_hash)
        urls_by_path[item_path].add(item_url)

    _print_dupstats()


def _without_key(dict_, key):
    return {k: v for k, v in dict_.items() if k != key}


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

    def update(self, dup, nodup):
        self.dup += len(dup)
        self.nodup += nodup if isinstance(nodup, int) else len(nodup)

    def __repr__(self):
        return '<DupStat: {:.0f}% (of {})>'.format(
            100 * self.dup / self.total, self.total)


def parse_url(url):
    p = urlsplit(url)
    query = {k: v[0] for k, v in parse_qs(p.query).items() if len(v) == 1}
    return ''.join([p.netloc, p.path]), query


if __name__ == '__main__':
    main()
