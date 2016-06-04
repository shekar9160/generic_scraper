#!/usr/bin/env python
import argparse
import gzip
import json
from collections import defaultdict
from functools import partial
import os

from scrapy.utils.url import canonicalize_url


normalize_url = partial(canonicalize_url, keep_fragments=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('folder')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--full-items', action='store_true')
    args = parser.parse_args()

    urls_by_team = defaultdict(set)
    fp_by_team = defaultdict(set)
    if args.full_items:
        for team, items in team_item_reader(args.folder, limit=args.limit):
            print('Reading team {}...'.format(team))
            for item in items:
                urls_by_team[team].add(normalize_url(item['url']))
    else:
        for fp, team, url in team_hash_reader(args.folder):
            urls_by_team[team].add(normalize_url(url))
            fp_by_team[team].add(fp)

    print()
    print_stats(urls_by_team, 'Urls')
    print()
    print_stats(fp_by_team, 'Fp')


def print_stats(by_team, name):
    teams = sorted(by_team)
    print('{}\t{}'.format(name, '\t'.join(teams)))
    for team1 in teams:
        print(team1, end='\t')
        for team2 in teams:
            if team1 <= team2:
                print(len(by_team[team1] & by_team[team2]), end='\t')
            else:
                print('\t', end='')
        print()


def team_hash_reader(root):
    for line in gzip.open(os.path.join(root, 'hashes.gz')):
        hash, team, url = line.decode('utf-8').strip().split()
        yield hash, team, url


def team_item_reader(root, limit=None):
    for filename in sorted(os.listdir(root)):
        if filename.endswith('.json.gz'):
            team = filename.split('.')[0].upper()
            yield team, item_reader(os.path.join(root, filename), limit=limit)


def item_reader(path, limit=None):
    with gzip.open(path) as f:
        for n, line in enumerate(f):
            if limit is not None and n >= limit:
                break
            yield json.loads(line.decode('utf-8').strip())


if __name__ == '__main__':
    main()