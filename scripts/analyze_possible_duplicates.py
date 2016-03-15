#!/usr/bin/env python
import argparse, json, os
from collections import namedtuple, defaultdict
from hashlib import sha1
from urllib.parse import urlsplit

from tqdm import tqdm
import lxml.html
from datasketch import MinHash, LSH


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('cralwer_out_dir')
    args = parser.parse_args()

    print('site'.ljust(40), '\t'.join([
        'urls', 'set(u)', 'set(paths)', 'reduction']))
    for filename in os.listdir(args.cralwer_out_dir):
        with open(os.path.join(args.cralwer_out_dir, filename)) as f:
            analyze_file(filename, f)


def analyze_file(name, f):
    urls = []
    Doc = namedtuple('Doc', ['item', 'min_hash'])
    documents = {} # key -> Doc
    lsh = LSH(threshold=0.9, num_perm=128)
    shingle_counts = defaultdict(int)
    for item in item_reader(f, name):
        hashes = set(shingle_h.hexdigest()
            for shingle_h in shingle_hashes(item['text_content']))
        for h in hashes:
            shingle_counts[h] += 1
    max_sh_count = max(shingle_counts.values())
    too_common = set(h for h, count in shingle_counts.items()
                     if count > 0.1 * max_sh_count)
    for i, item in enumerate(item_reader(f, name)):
        urls.append(item['url'])
        min_hash = MinHash(num_perm=128)
        for shingle_h in shingle_hashes(item['text_content']):
            if shingle_h.hexdigest() not in too_common:
                min_hash.digest(shingle_h)
        key = 'item_{}'.format(i)
        documents[key] = Doc(item, min_hash)
        lsh.insert(key, min_hash)
    paths = [''.join([p.netloc, p.path]) for p in map(urlsplit, urls)]
    for key, (item, min_hash) in documents.items():
        candidates = set(lsh.query(min_hash))
        if key in candidates:
            candidates.remove(key)
        if candidates:
            print()
            print(item['url'])
            for k in candidates:
                print(documents[k].item['url'])
    print(name.ljust(40), '\t'.join(map(str, [
        len(urls), len(set(urls)), len(set(paths)),
        '%.1f' % (len(set(urls)) / len(set(paths)))])))


def item_reader(f, name):
    n_skips = 0
    f.seek(0)
    n_lines = sum(1 for _ in f)
    f.seek(0)
    for i, line in tqdm(enumerate(f), total=n_lines):
        if i > n_lines:
            break
        try:
            item = json.loads(line.strip('[],\n'))
        except ValueError:
            n_skips += 1
            continue
        item['text_content'] = \
            lxml.html.document_fromstring(item['text']).text_content()
        yield item
    assert n_skips <= 1, (n_skips, name)


def shingle_hashes(text):
    n = 4
    words = text.split()
    for idx in range(n, len(words)):
        yield sha1(' '.join(words[idx - n : idx]).encode('utf-8'))


if __name__ == '__main__':
    main()
