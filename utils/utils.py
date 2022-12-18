import logging
import ipaddress
import math
import socket
import sys
from typing import Mapping, MutableMapping, MutableSequence, Sequence, Union
import yaml
import os
import requests


def load_yaml(url_or_path: str) -> dict:
    logging.info(f'load yaml file from {url_or_path}')
    try:
        ret = load_yaml_from_path(url_or_path)
    except FileNotFoundError as fileNotFoundError:
        try:
            ret = load_yaml_from_url(url_or_path)
        except (
            requests.exceptions.MissingSchema,
            requests.exceptions.InvalidSchema,
        ):
            raise fileNotFoundError
    return ret


def load_yaml_from_url(url: str):
    timeout = 10

    headers = {'charset': 'utf-8'}
    r = requests.get(
        url=url,
        headers=headers,
        timeout=timeout,
    )
    ret = yaml.safe_load(r.text)
    return ret


def load_yaml_from_path(path: str):
    if not os.path.isfile(path):
        raise FileNotFoundError(f'{path} not found')
    with open(path, 'r') as fd:
        ret = yaml.safe_load(fd)
    return ret


def make_simple_clash_config(
    controller_port: int, proxy_port: int, proxies: MutableSequence[MutableMapping]
):
    config = {
        'external-controller': f':{controller_port}',
        'port': proxy_port,
        'ipv6': True,
        'mode': 'global',
    }
    config.update({'proxies': proxies})
    return config


def my_nslookup(hostname):
    try:
        r = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return None
    return [e[4][0] for e in r]


def get_egress_ip(proxy: Union[None, Mapping]):
    r = requests.get('https://api64.ipify.org', proxies=proxy, timeout=10)
    return r.text


def designate_jobs(jobs: Sequence, max_worker_count: int):
    """

    Notice
    ---
    Order kept.
    """
    duties = [math.ceil(len(jobs) / max_worker_count)] * max_worker_count
    designated_duties = sum(duties)
    difference = len(jobs) - designated_duties
    for i in range(abs(difference)):
        duties[i] += difference // abs(difference)
    try:
        duties.remove(0)
    except ValueError:
        pass
    last = 0
    ret = []
    for duty in duties:
        ret.append(jobs[last : last + duty])
        last += duty
    return ret


def is_tcp_port_in_use(port: int, addr='127.0.0.1', timeout=0.01):
    s = None
    ret = False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((addr, port))
        ret = True
        s.close()
    except socket.error:
        pass
    return ret


def get_tcp_port_picker(port=1024):
    max_port = 65535
    while port <= max_port:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('', port))
            sock.close()
            yield port
        except OSError:
            pass
        port += 1

    raise IOError('no free tcp ports')
