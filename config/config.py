import logging
import yaml
from typing import List, MutableMapping, Union
import re
from .proxy import Proxy


class Config:
    def __init__(self, data: MutableMapping) -> None:
        self.data = data
        self.proxies = self._get_proxies()

    def _get_proxies(self):
        proxies: Union[List[Proxy], None]
        try:
            proxies = [Proxy(p) for p in self.data['proxies']]
        except KeyError:
            proxies = None
        return proxies

    def save(self, path):
        pass

    @property
    def controller(self):
        regex = re.compile(r'(.*?):(\d+)')
        _, addr, port, _ = regex.split(self.data['external-controller'])
        if not addr:
            addr = '127.0.0.1'
        return f'http://{addr}:{port}'

    @property
    def proxy(self):
        port: int
        try:
            port = self.data['port']
        except KeyError:
            try:
                port = self.data['mixed-port']
            except KeyError as e:
                logging.info(yaml.dump(self.data))
                raise e('http(s) proxy port needed')
        return f'http://127.0.0.1:{port}'

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value
