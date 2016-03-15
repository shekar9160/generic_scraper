#!/usr/bin/env python
import argparse, os, pwd, re, subprocess, sys


tpl = '''\
[program:{name}]
user = {user}
environment = LANG="en_US.UTF-8", USER="{user}"
directory = {root}
command = {scrapy} crawl base -a url={url} -s LOG_FILE={log} -o {out} -s JOBDIR={job} {extra}
log_stderr = true
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('urls')
    parser.add_argument('config_out_dir')
    parser.add_argument('data_out_dir')
    sys_args = sys.argv[1:]
    n_args = 3
    args = parser.parse_args(args=sys_args[:n_args])
    other_args = ' '.join(sys_args[n_args:])

    dirs = [os.path.join(args.data_out_dir, name)
            for name in ['log', 'out', 'job']]
    for d in dirs:
        os.makedirs(d, exist_ok=True)

    with open(args.urls) as f:
        urls = [_normalize_url(line) for line in f]

    names = set()
    for url in urls:
        name = _unique_name(url, names)
        names.add(name)
        print(name, url)

        with open(os.path.join(args.config_out_dir, name + '.conf'), 'w') as f:
            dout = lambda d, x: os.path.join(args.data_out_dir, d, x)
            f.write(tpl.format(
                name=name,
                user=pwd.getpwuid(os.getuid()).pw_name,
                root=os.path.abspath(os.path.dirname(__file__)),
                scrapy=subprocess.check_output(
                    ['which', 'scrapy']).strip().decode('utf-8'),
                url=url,
                log=dout('log', name + '.log'),
                out=dout('out', name + '.json'),
                job=dout('job', name),
                extra=other_args,
                ))


def _unique_name(url, names):
    name = re.sub(r'^(^https?://)?(www\.)?', '', url)
    name = re.sub(r'[^a-zA-Z]', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    _name = name
    n = 0
    while name in names:
        n += 1
        name = '{}_{}'.format(_name, n)
    return name


def _normalize_url(line):
    url = line.strip()
    if not url.startswith('http'):
        url = 'http://' + url
    return url


if __name__ == '__main__':
    main()
