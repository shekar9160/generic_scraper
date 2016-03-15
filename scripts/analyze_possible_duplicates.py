#!/usr/bin/env python
import argparse, json, os
from collections import namedtuple
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
    n_skips = 0
    lsh = LSH(threshold=0.9, num_perm=128)
    n_lines = sum(1 for _ in f)
    f.seek(0)
    for i, line in tqdm(enumerate(f), total=n_lines):
        if i >= n_lines:
            break
        try:
            item = json.loads(line.strip('[],\n'))
        except ValueError:
            n_skips += 1
            continue
        urls.append(item['url'])
        text = lxml.html.document_fromstring(item['text']).text_content()
        min_hash = MinHash(num_perm=128)
        n = 4
        words = text.split()
        for idx in range(n, len(words)):
            shingle = ' '.join(words[idx - n : idx])
            min_hash.digest(sha1(shingle.encode('utf-8')))
        key = 'item_{}'.format(i)
        documents[key] = Doc(item, min_hash)
        lsh.insert(key, min_hash)
    assert n_skips <= 1, (n_skips, name)
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



if __name__ == '__main__':
    main()
