#!/usr/bin/env python
import argparse, json, os
from collections import Counter

from datasketch import MinHashLSH
from maybedont.utils import get_min_hash

from scripts.utils import item_reader, get_too_common_shingles


def main():
    parser = argparse.ArgumentParser()
    arg = parser.add_argument
    arg('crawler_out')
    arg('--show', help='show urls for given key')
    arg('--skip-unique', action='store_true', help='skip unique check')
    arg('--duration-limit', type=int, help='in seconds')
    arg('--print-duplicates', action='store_true')
    arg('--print-urls', action='store_true')
    arg('--limit', type=int)
    arg('--max-int-value', type=int, default=5)
    arg('--output', help='additional output in JSON')
    args = parser.parse_args()

    params = vars(args)
    crawler_out = params.pop('crawler_out')
    output = params.pop('output')
    stats = {}
    if os.path.isdir(crawler_out):
        for filename in os.listdir(crawler_out):
            if filename.endswith('.json') or filename.endswith('.jl'):
                with open(os.path.join(crawler_out, filename)) as f:
                    print()
                    print(filename)
                    stats[filename] = print_stats(f, **params)
    else:
        with open(crawler_out) as f:
            stats[os.path.basename(crawler_out)] = print_stats(f, **params)
    if output:
        with open(output, 'w') as f:
            json.dump(stats, f, ensure_ascii=False, indent=4, sort_keys=True)


def print_stats(
        f, show=None, skip_unique=False, max_int_value=5, duration_limit=None,
        print_duplicates=False, print_urls=False, limit=None):
    stats = Counter()
    if not skip_unique:
        lsh = MinHashLSH(threshold=0.9, num_perm=128)
        too_common = get_too_common_shingles(f, limit=1000)
    urls = {}
    min_timestamp = max_timestamp = None
    for i, item in enumerate(item_reader(f, limit=limit)):
        if print_urls:
            print(item['url'])
        content_type = item.get('content_type', 'missing')
        stats.update([
            'content_type: ' + content_type,
            'content_type[0]: ' + content_type.split('/')[0]])
        if min_timestamp is None:
            min_timestamp = item['timestamp']
        max_timestamp = item['timestamp']
        if duration_limit and \
                (max_timestamp - min_timestamp) / 1000 > duration_limit:
            break
        if 'extracted_text' not in item:
            assert item['obj_stored_url']
            stats.update(['documents'])
            continue
        stats.update(['items'])
        for key, value in item['extracted_metadata'].items():
            if key == 'forms':
                for form in value:
                    stats.update(['form_{}'.format(form['form'])])
                    stats.update(['form_field {}'.format(f)
                                  for f in form['fields'].values()])
            if isinstance(value, list):
                value = len(value)
            if isinstance(value, int) and not isinstance(value, bool):
                if value >= max_int_value:
                    value = '{}+'.format(max_int_value)
                key = '{}_{}'.format(key, value)
            if value:
                stats.update([key])
                if key == show:
                    print(item['url'])
        if not skip_unique:
            min_hash = get_min_hash(item['extracted_text'], too_common)
            duplicates = lsh.query(min_hash)
            if not duplicates:
                stats.update(['unique_items'])
            elif print_duplicates:
                print('{} {} duplicates: {}'.format(
                    item['url'], len(duplicates),
                    ' '.join(urls[k] for k in duplicates[:10])))
            key = 'item_{}'.format(i)
            lsh.insert(key, min_hash)
            urls[key] = item['url']

    if max_timestamp and min_timestamp:
        stats['duration'] = (max_timestamp - min_timestamp) / 1000
    for k, v in sorted(stats.items()):
        print(k.ljust(20), v)
    return stats


if __name__ == '__main__':
    main()
