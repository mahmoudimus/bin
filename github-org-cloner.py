#!/usr/bin/env python
"""
Use like so:

github-org-cloner.py <starting-url>

Clones into directory where script was invoked from.
"""
import os
import sys
import getpass
import subprocess
import ConfigParser

import requests


def _colorize(msg):
    start = '\033[91m'
    end = '\033[0m'
    return "{start}ERROR{end}: {msg}".format(start=start, end=end, msg=msg)


def error(msg):
    print >> sys.stderr, _colorize(msg)


def _parse_link_header(links):
    """
    >>> import pprint
    >>> links = ('<https://api.github.com/user/repos?page=3&per_page=100>;'
    ...          'rel="next",'
    ...          '<https://api.github.com/user/repos?page=50&per_page=100>;'
    ...          'rel="last"')
    >>> parsed = _parse_link_header(links)
    >>> sorted(parsed.keys())
    ['last', 'next']
    >>> pprint.pprint(sorted(parsed.values()))
    ['https://api.github.com/user/repos?page=3&per_page=100',
     'https://api.github.com/user/repos?page=50&per_page=100']
    """
    links = links.split(',')
    parsed = {}
    for link in links:
        # take <https://api.github.com/user/repos?page=3>; rel="next"
        # split it into https://api.github.com/user/repos?page=3, next
        url, rel = link.strip().split(';')
        sanitized_url = url.strip('<>')
        _, _, direction = rel.replace('"', '').partition('=')
        parsed[direction] = sanitized_url
    return parsed


# 'https://api.github.com/orgs/balanced-cookbooks/repos'
REPO_URLS = [sys.argv[1]]
PAGE = 1
ERRORS = []
config = ConfigParser.ConfigParser()
cfgfile = os.path.expanduser('~/.github.cfg')


try:

    with open(cfgfile) as gh:
        config.readfp(gh)
        user = config.get('credentials', 'user')
        password = config.get('credentials', 'password')
        print 'Loaded previous configuration from {} for user: {}'.format(
            cfgfile, user)
except (IOError, ConfigParser.NoSectionError):
    user = raw_input('Github user: ')
    password = getpass.getpass('Password: ')
    try:
        with open(cfgfile, 'w+') as gh:
            config.add_section('credentials')
            config.set('credentials', 'user', user)
            config.set('credentials', 'password', password)
            config.write(gh)
    except IOError:
        pass


for url in REPO_URLS:
    res = requests.get(url, auth=(user, password))
    if res.status_code == 401:
        raise ValueError(
            _colorize('Password for user "{}" is incorrect!'.format(user))
        )

    try:
        links = _parse_link_header(res.headers['link'])
        next_link = links['next']
        REPO_URLS.append(next_link)
    except KeyError:
        pass

    json_data = res.json()

    for repo in json_data:
        url = repo['ssh_url']
        repo_name = repo['name']
        if os.path.exists(repo_name):
            cwd = os.path.join(os.getcwd(), repo_name)
            git_ref = subprocess.check_output(
                ['git', 'symbolic-ref', 'HEAD'], cwd=cwd
            )
            _, _, current_branch = git_ref.strip().rpartition('/')
            print 'Repo {} already exists, updating {}'.format(
                repo_name,
                current_branch
            )
            cmds = [
                ['git', 'pull', 'origin', current_branch],
                ['git', 'pull'],
            ]
            for c in cmds:
                retcode = subprocess.call(c, cwd=cwd)
                if retcode != 0:
                    ERRORS.append({
                        'repo': repo_name,
                        'error_code': retcode,
                    })
                    error("Couldn't update: {}. Moving on".format(repo_name))
        else:
            print 'Cloning {}'.format(repo_name)
            subprocess.check_call(['git', 'clone', url])


for e in ERRORS:
    error("Couldn't update {}. Returned errcode: {}".format(
        e['repo'],
        e['error_code']
    ))
