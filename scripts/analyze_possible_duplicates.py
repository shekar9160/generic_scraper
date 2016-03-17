#!/usr/bin/env python
import argparse, os
from collections import namedtuple, defaultdict
from hashlib import sha1
from urllib.parse import urlsplit

from datasketch import MinHash, LSH

from scripts.utils import item_reader


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('cralwer_out_dir')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    print('site'.ljust(40), '\t'.join(['urls', 'set(u)', 'pth', 'uniq']))
    for filename in os.listdir(args.cralwer_out_dir):
        with open(os.path.join(args.cralwer_out_dir, filename)) as f:
            analyze_file(filename, f, verbose=args.verbose)


def analyze_file(name, f, verbose=False):
    urls = []
    Doc = namedtuple('Doc', ['item', 'min_hash'])
    documents = {} # key -> Doc
    lsh = LSH(threshold=0.9, num_perm=128)
    shingle_counts = defaultdict(int)
    for item in item_reader(f, name, limit=300):
        hashes = set(shingle_h.hexdigest()
            for shingle_h in shingle_hashes(item['extracted_text']))
        for h in hashes:
            shingle_counts[h] += 1
    max_sh_count = max(shingle_counts.values())
    too_common = set(h for h, count in shingle_counts.items()
                     if count > 0.1 * max_sh_count)
    for i, item in enumerate(item_reader(f, name)):
        urls.append(item['url'])
        min_hash = MinHash(num_perm=128)
        for shingle_h in shingle_hashes(item['extracted_text']):
            if shingle_h.hexdigest() not in too_common:
                min_hash.digest(shingle_h)
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


def shingle_hashes(text):
    n = 4
    words = text.split()
    for idx in range(n, len(words)):
        yield sha1(' '.join(words[idx - n : idx]).encode('utf-8'))


if __name__ == '__main__':
    main()
