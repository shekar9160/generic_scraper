#!/usr/bin/env python
import argparse, json, os
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('cralwer_out_dir')
    args = parser.parse_args()

    print('site'.ljust(40), '\t'.join([
        'urls', 'set(u)', 'set(paths)', 'reduction']))
    for filename in os.listdir(args.cralwer_out_dir):
        with open(os.path.join(args.cralwer_out_dir, filename)) as f:
            urls = []
            n_skips = 0
            for line in f:
                try:
                    urls.append(json.loads(line.strip('[],\n'))['url'])
                except ValueError:
                    n_skips += 1
            assert n_skips <= 1, (n_skips, filename)
            paths = [''.join([p.netloc, p.path]) for p in map(urlsplit, urls)]
            print(filename.ljust(40), '\t'.join(map(str, [
                len(urls), len(set(urls)), len(set(paths)),
                '%.1f' % (len(set(urls)) / len(set(paths)))])))


if __name__ == '__main__':
    main()
