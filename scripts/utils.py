import json

from tqdm import tqdm


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
