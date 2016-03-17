#!/usr/bin/env python
import argparse, os
from collections import Counter

from scripts.utils import item_reader


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('cralwer_out')
    parser.add_argument('--show')
    args = parser.parse_args()

    params = {'show': args.show}
    if os.path.isdir(args.cralwer_out):
        for filename in os.listdir(args.cralwer_out_dir):
            with open(os.path.join(args.cralwer_out_dir, filename)) as f:
                print()
                print(filename)
                print_stats(f, **params)
    else:
        with open(args.cralwer_out) as f:
            print_stats(f, **params)


def print_stats(f, show=None):
    meta_counts = Counter()
    for item in item_reader(f):
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
    for k, v in sorted(meta_counts.items()):
        print(k.ljust(20), v)


if __name__ == '__main__':
    main()
