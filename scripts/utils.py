import json

from tqdm import tqdm
import maybedont.utils


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


def get_too_common_shingles(f, name=None, limit=None):
    return maybedont.utils.get_too_common_shingles(
        (item['extracted_text'] for item in item_reader(f, name, limit=limit)
            if 'extracted_text' in item))
