import logging
import yaml
from os import PathLike
from typing import Iterable, List, Mapping, MutableMapping

from config.proxy import Proxy
from .config import Config
from . import subscription_config_collection as scc


class TemplateConfig(Config):
    def __init__(self, data: MutableMapping, geometry_key: str) -> None:
        super().__init__(data=data)
        self.geometry_key = geometry_key

    def inject(self, country_map: scc.types.CountryMap):
        def get_names(proxies: List[Proxy]):
            return [proxy['name'] for proxy in proxies]

        all_proxies = []
        for proxies in country_map.values():
            all_proxies += proxies

        for proxy_group in self['proxy-groups']:
            if 'proxies' not in proxy_group.keys():
                # create 'proxies' key if necessary
                proxy_group['proxies'] = []
            elif (
                proxy_group['proxies']
                and self.geometry_key in proxy_group.keys()
                and proxy_group[self.geometry_key] == None
            ):
                # skip injection when the proxy group
                # 1. already have non-empty 'proxies'
                # 2. have empty 'geometry_key'
                continue

            # no geometry need
            if self.geometry_key not in proxy_group.keys():
                proxy_group['proxies'] += get_names(all_proxies)
                continue

            # need geometry
            for iso_code in proxy_group[self.geometry_key]:
                if iso_code in country_map.keys():
                    proxy_group['proxies'] += get_names(country_map[iso_code])

            # if no proxies added, warning and then fill with all proxies
            if not proxy_group['proxies']:
                logging.warning(
                    f'no {proxy_group[self.geometry_key]} proxies for proxy '
                    f'group {proxy_group["name"]}'
                )
                proxy_group['proxies'] += all_proxies

            # remove geometry key
            proxy_group.pop(self.geometry_key)

        if 'proxies' not in self.data:
            self['proxies'] = []
        self['proxies'] += [proxy.data for proxy in all_proxies]

    def save(self, path: PathLike):
        with open(path, 'w') as fd:
            yaml.safe_dump(self.data, fd, allow_unicode=True)
        logging.info(f'config is saved to {path}')
