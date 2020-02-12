#!/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import re
import logging
import argparse
import requests
try:
    # python3
    from urllib.parse import urljoin
except:
    pass
try:
    from urlparse import urljoin
except:
    pass

logging.basicConfig(level=logging.DEBUG)

# Github rest api docs: https://developer.github.com/v3/
GITHUB_API_URL = "https://api.github.com"
GITHUB_API_ACCEPT_HEADER="application/vnd.github.v3+json"

# Get the github auth from the environment (if present)
# The GITHUB_AUTH environment variable should contain username and authentication (token or password), separated
# by a colon (:) i.e.: myusername:mytokenorpassword
# The token is recommended and permissions can be completely restricted as the data requested in this script is
# publicly available anyway. The reason we might need authentication is to overcome the fairly limited default rate
# limit of the github rest api of 60 requests per hour.
GITHUB_AUTH=None
try:
    github_auth = os.getenv('GITHUB_AUTH', None)
    if github_auth is not None:
        GITHUB_AUTH = tuple(github_auth.split(':'))
except Exception:
    pass


def get_all_pages(github_api_url):
    """Get all pages of a given github API V3 URL.

    This function follows github api pagination information until all pages for the root url have been read.
    """
    logging.debug('URL: {}'.format(github_api_url))
    resp = requests.get(github_api_url, headers={'Accept': GITHUB_API_ACCEPT_HEADER}, auth=GITHUB_AUTH)
    if not resp.ok:
        logging.debug("GET {} response: {}".format(github_api_url, resp))
        return

    result = resp.json()
    while 'next' in resp.links.keys():
        next_url = resp.links['next']['url']
        logging.debug('URL: {}'.format(next_url))
        resp = requests.get(next_url, headers={'Accept': GITHUB_API_ACCEPT_HEADER}, auth=GITHUB_AUTH)
        result.extend(resp.json())
    return result


def get_latest_release(organisation, repo):
    url = urljoin(GITHUB_API_URL, "repos/{organisation}/{repo}/releases/latest"
                  .format(organisation=organisation, repo=repo))
    resp = requests.get(url, headers={'Accept': GITHUB_API_ACCEPT_HEADER}, auth=GITHUB_AUTH)
    if not resp.ok:
        logging.debug("GET {} response: {}".format(url, resp))
        return

    release = resp.json()
    return release


def get_latest_tag(organisation, repo):
    url = urljoin(GITHUB_API_URL, "repos/{organisation}/{repo}/tags"
                  .format(organisation=organisation, repo=repo))
    tags = get_all_pages(url)
    if tags is None:
        return None
    regexp_version = re.compile(r'^R?\d+[\-\.]\d+([\-\.]\d+)?$')
    tag_names = [tag['name'] for tag in tags if regexp_version.match(tag['name'])]
    tag_names.sort(reverse=True)
    latest_tag_name = tag_names[0]
    for tag in tags:
        if tag['name'] == latest_tag_name:
            return tag


def latest_release(organisation, repo):
    """Get the latest release from a github repo

    A full 'github release' is first requested. If one is not available, the repo is searched for tags and the highest
    release tag is returned."""
    release = get_latest_release(organisation, repo)
    if release is None:
        release = get_latest_tag(organisation, repo)
        if release is not None:
            # make the tag dict somewhat compatible with the release dict
            release.update({'tag_name': release['name']})
    return release


def main():
    parser = argparse.ArgumentParser(description='Get latest release version number from a github repo')
    parser.add_argument('organisation', type=str,
                        help='Name of github organisation')
    parser.add_argument('repo', type=str,
                        help='Name of the github repository with the organisation')
    parser.add_argument("-t", "--tarball", help="Print URL to release tarball",
                        action="store_true")
    args = parser.parse_args()
    logging.debug(args)

    release = latest_release(args.organisation, args.repo)
    if release is None:
        return -1

    if args.tarball:
        sys.stdout.write(release['tarball_url'])
        return 0
    sys.stdout.write(release['tag_name'])
    return 0


if __name__ == "__main__":
    exit(main())
