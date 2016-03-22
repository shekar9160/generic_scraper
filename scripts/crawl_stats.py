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


def print_stats(f, show=None, skip_unique=False):
    meta_counts = Counter()
    if not skip_unique:
        lsh = LSH(threshold=0.9, num_perm=128)
        too_common = get_too_common_shingles(f, limit=1000)
    for i, item in enumerate(item_reader(f)):
        meta_counts.update(['items'])
        for key, value in item['extracted_metadata'].items():
            if isinstance(value, int) and not isinstance(value, bool):
                key = '{}_{}'.format(key, value)
            elif isinstance(value, list):
                key = '{}_{}'.format(key, len(value))
            if value:
                meta_counts.update([key])
                if key == show:
                    print(item['url'])
        if not skip_unique:
            min_hash = get_min_hash(item['extracted_text'], too_common)
            if not lsh.query(min_hash):
                meta_counts.update(['unique_items'])
            lsh.insert('item_{}'.format(i), min_hash)
    for k, v in sorted(meta_counts.items()):
        print(k.ljust(20), v)


if __name__ == '__main__':
    main()
