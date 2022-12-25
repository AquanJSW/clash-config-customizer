import argparse
from geoip2.database import Reader
from geoip2.types import IPAddress
from geoip2.models import Country
import gzip
import io
from zipfile import ZipFile

import requests
from utils import load_yaml
import pathlib
import os
from typing import *
import logging

clash_url_linux = (
    'https://release.dreamacro.workers.dev/latest/clash-linux-amd64-latest.gz'
)
clash_url_windows = (
    'https://release.dreamacro.workers.dev/latest/clash-windows-amd64-latest.zip'
)
clash_bin_name_linux = 'clash-linux-amd64'
clash_bin_name_windows = 'clash-windows-amd64.exe'
clash_extract_dir = os.path.abspath('assets')

mmdb_url = 'https://git.io/GeoLite2-Country.mmdb'
mmdb_download_dir = os.path.expanduser('assets')

OUTPUT_DIR = 'output'


class Layout:
    # from arguments
    subscription_configs: Iterable[Mapping] = []
    '''No guarantee of validity'''
    template_configs: Iterable[Mapping] = []
    '''No guarantee of validity'''
    output_paths: Iterable[str]
    prefixes: Iterable[str]
    enable_renames: Iterable[bool]
    clash_bin: str
    get_geometry: Callable[[IPAddress], Country]

    # manual set
    geometry_key = 'country'
    proxy_name_fmt_4 = '{iso_code}.{seq:02}'
    proxy_name_fmt_6 = 'IPv6.' + proxy_name_fmt_4


def is_enable_renames_valid(enable_renames):
    s = set(['0', '1'])
    r = set(enable_renames)
    return r < s


def download_clash():
    """

    Return
    ---
    Path of Clash binary.
    """
    os.makedirs(clash_extract_dir, exist_ok=True)
    if os.name == 'nt':
        path = os.path.join(clash_extract_dir, clash_bin_name_windows)
        if os.path.exists(path):
            logging.info(f'Clash bin exists, delete {path} if you wanna re-download.')
            return path
        url = clash_url_windows
        logging.info(f'download clash from {url}')
        r = requests.get(url)
        data = r.content
        zf = ZipFile(io.BytesIO(data))
        zf.extractall(clash_extract_dir)
        return path
    else:
        path = os.path.join(clash_extract_dir, clash_bin_name_linux)
        if os.path.exists(path):
            logging.info(f'Clash bin exists, delete {path} if you wanna re-download.')
            return path
        url = clash_url_linux
        logging.info(f'download clash from {url}')
        r = requests.get(url)
        data = r.content
        data = gzip.decompress(data)
        with open(path, 'wb') as fd:
            fd.write(data)
        os.chmod(path, 0o775)
        return path


def download_mmdb():
    filename = mmdb_url.split('/')[-1]
    path = os.path.join(mmdb_download_dir, filename)
    if os.path.exists(path):
        logging.info(f'mmdb exist, delete {path} if you wanna update.')
        return path
    logging.info(f'downloading mmdb database from {mmdb_url}')
    r = requests.get(mmdb_url)
    data = r.content
    with open(path, 'wb') as fd:
        fd.write(data)
    return path


def set_layout(args: argparse.Namespace):
    # verbose set
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%m-%d %H:%M:%S',
        force=True,
    )
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    # nargs check
    assert len(args.subscription_configs) == len(args.prefixes)
    assert len(args.template_configs) == len(args.output_names)

    # load proxy
    # adapt the proxy config to requests package
    # Notice: No guarantee of validation
    if os.environ.get('https_proxy') is not None:
        Layout.proxy = {'https': os.environ.get('https_proxy')}

    # load subscription configs
    Layout.subscription_configs = [load_yaml(x) for x in args.subscription_configs]

    # load & check template configs
    for src in args.template_configs:
        config = load_yaml(src)
        if 'proxy-groups' not in config.keys():
            raise KeyError(f'no "proxy-groups" in config {src}')
        Layout.template_configs.append(config)

    # outputs
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    Layout.output_paths = [os.path.join(OUTPUT_DIR, name) for name in args.output_names]

    # prefix assign
    Layout.prefixes = [str(x) for x in args.prefixes]

    # check and assign enable-rename
    if not is_enable_renames_valid(args.enable_renames):
        raise ValueError('enable_renames only accept value 0 or 1')
    Layout.enable_renames = [bool(int(x)) for x in args.enable_renames]

    # Clash binary
    Layout.clash_bin = download_clash()
    mmdb_path = download_mmdb()
    Layout.get_geometry = lambda ip: Reader(mmdb_path).country(ip)
