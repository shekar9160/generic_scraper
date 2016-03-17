import json
from hashlib import sha1
from collections import defaultdict

from tqdm import tqdm
from datasketch import MinHash


def item_reader(f, name=None, limit=None):
    n_skips = 0
    f.seek(0)
    if limit is None:
        limit = sum(1 for _ in f)
        f.seek(0)
    for i, line in tqdm(enumerate(f), total=limit):
        if i > limit:
            break
        try:
            item = json.loads(line.strip('[],\n'))
        except ValueError:
            n_skips += 1
            continue
        yield item
    assert n_skips <= 1, (n_skips, name)


def shingle_hashes(text):
    n = 4
    words = text.split()
    for idx in range(n, len(words)):
        yield sha1(' '.join(words[idx - n : idx]).encode('utf-8'))


def get_too_common_shingles(f, name=None, limit=None):
    shingle_counts = defaultdict(int)
    for item in item_reader(f, name, limit=limit):
        hashes = set(shingle_h.hexdigest()
            for shingle_h in shingle_hashes(item['extracted_text']))
        for h in hashes:
            shingle_counts[h] += 1
    max_sh_count = max(shingle_counts.values())
    too_common = set(h for h, count in shingle_counts.items()
                     if count > 0.1 * max_sh_count)
    return too_common


def get_min_hash(item, too_common):
    min_hash = MinHash(num_perm=128)
    for shingle_h in shingle_hashes(item['extracted_text']):
        if shingle_h.hexdigest() not in too_common:
            min_hash.digest(shingle_h)
    return min_hash
