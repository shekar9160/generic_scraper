import json
from hashlib import sha1
from collections import defaultdict

from tqdm import tqdm
from datasketch import MinHash


def item_reader(f, name=None, limit=None, skip_limit=False):
    n_skips = 0
    f.seek(0)
    if limit is None or skip_limit:
        limit = sum(1 for _ in f)
        f.seek(0)
    it = enumerate(f)
    if not skip_limit:
        it = tqdm(it, total=limit)
    for i, line in it:
        if i > limit:
            continue
        try:
            item = json.loads(line.strip('[],\n'))
        except ValueError:
            n_skips += 1
            continue
        yield item
    assert n_skips <= 1, (n_skips, name)


def shingle_hashes(text):
    n = 4
    for line in text.split('\n'):
        words = line.strip().split()
        if words:
            for idx in range(min(len(words), n), len(words) + 1):
                yield sha1(' '.join(
                    words[max(0, idx - n) : idx]).encode('utf-8'))


def get_too_common_shingles(f, name=None, limit=None):
    shingle_counts = defaultdict(int)
    n_items = 0
    for item in item_reader(f, name, limit=limit):
        n_items += 1
        hashes = set(shingle_h.hexdigest()
            for shingle_h in shingle_hashes(item['extracted_text']))
        for h in hashes:
            shingle_counts[h] += 1
    if shingle_counts:
        return set(h for h, count in shingle_counts.items()
                   if count > max(1, 0.05 * n_items))
    return set()


def get_min_hash(item, too_common):
    min_hash = MinHash(num_perm=128)
    for shingle_h in shingle_hashes(item['extracted_text']):
        if shingle_h.hexdigest() not in too_common:
            min_hash.digest(shingle_h)
    return min_hash
