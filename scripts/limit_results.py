#!/usr/bin/env python
import argparse, json, os

from scripts.utils import item_reader


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('cralwer_out')
    parser.add_argument('out')
    parser.add_argument('seconds', type=int)
    args = parser.parse_args()

    if os.path.isdir(args.cralwer_out):
        for filename in os.listdir(args.cralwer_out):
            print(filename)
            limit_results(
                os.path.join(args.cralwer_out, filename),
                os.path.join(args.out, filename),
                args.seconds)
    else:
        limit_results(args.cralwer_out, args.out, args.seconds)


def limit_results(in_filename, out_filename, seconds):
    with open(in_filename) as in_f:
        with open(out_filename, 'w') as out_f:
            out_f.write('[')
            start_timestamp = None
            n_items = 0
            for item in item_reader(in_f, skip_limit=True):
                if start_timestamp is None:
                    start_timestamp = item['timestamp']
                if item['timestamp'] - start_timestamp > seconds * 1000:
                    break
                if n_items != 0:
                    out_f.write(',\n')
                out_f.write(json.dumps(item))
                n_items += 1
            print(n_items)
            out_f.write(']\n')


if __name__ == '__main__':
    main()
