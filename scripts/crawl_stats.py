#!/usr/bin/env python
import argparse, os
from collections import Counter

from datasketch import LSH

from undercrawler.utils import get_min_hash
from scripts.utils import item_reader, get_too_common_shingles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('cralwer_out')
    parser.add_argument('--show', help='show urls for given key')
    parser.add_argument('--skip-unique', action='store_true',
                        help='skip unique check')
    parser.add_argument('--duration-limit', type=int, help='in seconds')
    args = parser.parse_args()

    params = vars(args)
    cralwer_out = params.pop('cralwer_out')
    if os.path.isdir(cralwer_out):
        for filename in os.listdir(cralwer_out):
            with open(os.path.join(cralwer_out, filename)) as f:
                print()
                print(filename)
                print_stats(f, **params)
    else:
        with open(cralwer_out) as f:
            print_stats(f, **params)


def print_stats(f, show=None, skip_unique=False, max_int_value=5,
                duration_limit=None):
    stats = Counter()
    if not skip_unique:
        lsh = LSH(threshold=0.9, num_perm=128)
        too_common = get_too_common_shingles(f, limit=1000)
    min_timestamp = max_timestamp = None
    for i, item in enumerate(item_reader(f)):
        if min_timestamp is None:
            min_timestamp = item['timestamp']
        max_timestamp = item['timestamp']
        if duration_limit and \
                (max_timestamp - min_timestamp) / 1000 > duration_limit:
            break
        stats.update(['items'])
        for key, value in item['extracted_metadata'].items():
            if isinstance(value, list):
                value = len(value)
            if isinstance(value, int) and not isinstance(value, bool):
                if value >= max_int_value:
                    value = '{}+'.format(max_int_value)
                key = '{}_{}'.format(key, value)
            if value:
                stats.update([key])
                if key == show:
                    print(item['url'])
        if not skip_unique:
            min_hash = get_min_hash(item['extracted_text'], too_common)
            if not lsh.query(min_hash):
                stats.update(['unique_items'])
            lsh.insert('item_{}'.format(i), min_hash)
    stats['duration'] = (max_timestamp - min_timestamp) / 1000
    for k, v in sorted(stats.items()):
        print(k.ljust(20), v)


if __name__ == '__main__':
    main()
