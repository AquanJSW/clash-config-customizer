from geoip2.errors import AddressNotFoundError
from ipaddress import ip_address
import multiprocessing
from os import PathLike
import signal
from clash import Clash
import sys
from utils import *
from typing import (
    Callable,
    Iterator,
    List,
    Mapping,
    Sequence,
    TypeAlias,
)
from .subscription_config import SubscriptionConfig
from .config import Proxy, Config
from geoip2.models import Country
from geoip2.types import IPAddress

NO_GEOMETRY_CODE = 'NOGEO'


class types:
    CountryMap: TypeAlias = Mapping[str, List[Proxy]]


def worker_ingress(proxy: Proxy):
    try:
        proxy.ingress_ip = ipaddress.ip_address(proxy['server'])
    except ValueError:
        records = my_nslookup(proxy['server'])
        if not records:
            # no record
            proxy.ingress_ip = None
        else:
            proxy.ingress_ip = [ipaddress.ip_address(record) for record in records][0]
    logging.info(f'[ingress] {str(proxy.ingress_ip)} {proxy["name"]}')
    return proxy


clash_bin = None


def worker_egress(proxies: Sequence[Proxy], ports: Sequence[int]):
    config = Config(
        make_simple_clash_config(
            controller_port=ports[0],
            proxy_port=ports[1],
            proxies=[proxy.data for proxy in proxies],
        )
    )
    clash = Clash(bin=clash_bin, config=config)
    for proxy in proxies:
        value = None
        if clash.switch_proxy(proxy['name']):
            try:
                value = ip_address(get_egress_ip({'https': clash.config.proxy}))
            except (
                requests.exceptions.Timeout,
                requests.exceptions.SSLError,
                requests.exceptions.ProxyError,
            ) as e:
                value = e
        proxy.egress_ip = value
        logging.info(f'[egress] {value} {proxy["name"]}')
    return proxies


class SubscriptionConfigCollection:
    """Subscription Config Collection Class"""

    def __init__(
        self,
        data: Sequence[Mapping],
        enable_renames: Sequence[bool],
    ) -> None:
        self.data = [
            SubscriptionConfig(data=config, enable_rename=enable_rename)
            for config, enable_rename in zip(data, enable_renames)
        ]
        self.proxies = self._get_proxies()

    def update_geometry(self, get_geometry: Callable[[IPAddress], Country]):
        logging.info('updating geometry info')
        for proxy in self.proxies:
            try:
                proxy.geometry = get_geometry(proxy.egress_ip)
            except AddressNotFoundError:
                logging.info(f'no geometry info for {str(proxy.egress_ip)}')

    def rename_proxies(
        self, proxy_name_fmt_4: str, proxy_name_fmt_6: str, prefixes=List[str]
    ):
        # find rename-enabled proxies and renamed-disabled proxies
        rename_enabled_proxies: List[Proxy] = []
        rename_disabled_proxies: List[Proxy] = []
        for subscription_config in self.data:
            if subscription_config.enable_rename:
                rename_enabled_proxies += subscription_config.proxies
            else:
                rename_disabled_proxies += subscription_config.proxies

        # create a dict from country.iso_code to the corresponding
        # rename-enabled proxies
        country_map: types.CountryMap = {}
        for proxy in rename_enabled_proxies:
            if proxy.geometry == None:
                # no geometry info, skip renaming
                rename_disabled_proxies.append(proxy)
                continue
            iso_code = proxy.geometry.country.iso_code
            if iso_code in country_map.keys():
                country_map[iso_code].append(proxy)
            else:
                country_map[iso_code] = [proxy]

        # rename
        for key, value in country_map.items():
            for i, proxy in enumerate(value):
                if isinstance(proxy.egress_ip, ipaddress.IPv4Address):
                    proxy['name'] = proxy_name_fmt_4.format(iso_code=key, seq=i)
                else:
                    proxy['name'] = proxy_name_fmt_6.format(iso_code=key, seq=i)

        # complement the country-map for return
        country_map[NO_GEOMETRY_CODE] = []
        for proxy in rename_disabled_proxies:
            if proxy.geometry == None:
                country_map[NO_GEOMETRY_CODE].append(proxy)
                continue
            iso_code = proxy.geometry.country.iso_code
            if iso_code in country_map.keys():
                country_map[iso_code].append(proxy)
            else:
                country_map[iso_code] = [proxy]

        # add prefix
        for subscription_config, prefix in zip(self.data, prefixes):
            subscription_config.add_prefix(prefix)

        return country_map

    def postprocess_proxies(self, get_geometry: Callable[[IPAddress], Country]):
        self.update_geometry(get_geometry)
        self.rename_proxies()

    def _get_proxies_by_country(self, iso_code: str):
        proxies = []
        for proxy in self.proxies:
            if proxy.geometry.country.iso_code == iso_code:
                proxies.append(proxy)
        return proxies

    def _get_proxies_by_continent(self, iso_code: str):
        proxies = []
        for proxy in self.proxies:
            if proxy.geometry.continent.iso_code == iso_code:
                proxies.append(proxy)
        return proxies

    def log_proxies_info(self):
        # full proxies info
        proxies_info = ''
        for i, proxy in enumerate(self.proxies):
            proxies_info += '-' * 80 + '\n' f'{i}\n' f'{proxy}\n'
        logging.debug(f'proxies info:\n{proxies_info[:-1]}')

        # invalid proxies info
        count_egress_Timeout = 0
        count_egress_SSLError = 0
        count_egress_ProxyError = 0
        count_ingress_NoRecord = 0
        indices_invalid = []
        for i, proxy in enumerate(self.proxies):
            if not proxy.ingress_ip:
                count_ingress_NoRecord += 1
                indices_invalid.append(i)
            if isinstance(proxy.egress_ip, requests.exceptions.Timeout):
                count_egress_Timeout += 1
                indices_invalid.append(i)
            elif isinstance(proxy.egress_ip, requests.exceptions.SSLError):
                count_egress_SSLError += 1
                indices_invalid.append(i)
            elif isinstance(proxy.egress_ip, requests.exceptions.ProxyError):
                count_egress_ProxyError += 1
                indices_invalid.append(i)
        invalid_proxies_info = ''
        for i in indices_invalid:
            invalid_proxies_info += '-' * 80 + '\n' f'{i}\n' f'{self.proxies[i]}\n'
        logging.debug(f'invalid proxies:\n{invalid_proxies_info[:-1]}')

        # summary
        logging.info(
            f'proxies summary:\n'
            f'total count: {len(self.proxies)}\n'
            f'ingress, no record count: {count_ingress_NoRecord}\n'
            f'egress, timeout count: {count_egress_Timeout}\n'
            f'egress, sslerror count: {count_egress_SSLError}\n'
            f'egress, proxyerror count: {count_egress_ProxyError}'
        )

    def purify_proxies(self):
        # remove redundant proxies (same ingress and egress IP)
        self.proxies = list(set(self.proxies))
        # remove invalid proxies
        self.proxies = [proxy for proxy in self.proxies if hash(proxy) != 0]
        logging.info(f'total proxy count after purify: {len(self.proxies)}')
        # update proxies in self.data (SubscriptionConfig s)
        for i, subscription_config in enumerate(self.data):
            count_before = len(subscription_config.proxies)
            subscription_config.proxies = set(subscription_config.proxies) & set(
                self.proxies
            )
            count_after = len(subscription_config.proxies)
            logging.info(f'change of config {i}: {count_before} -> {count_after}')
        pass

    def _get_proxies(self) -> List[Proxy]:
        ret = []
        for subscription_config in self.data:
            ret += subscription_config.proxies
        return ret

    def update_ingress_IPs(self):
        def init_worker():
            signal.signal(signal.SIGINT, signal.SIG_IGN)

        logging.info('Update ingress IP')
        try:
            pool = multiprocessing.Pool(os.cpu_count() + 1, init_worker)
            proxies = pool.map(worker_ingress, self.proxies)
            pool.close()
            pool.join()
        except KeyboardInterrupt:
            pool.terminate()
            pool.join()
            sys.exit(1)

        # value feed back
        for src, dst in zip(proxies, self.proxies):
            dst.ingress_ip = src.ingress_ip

    def update_egress_IPs(self, _clash_bin: PathLike):
        global clash_bin
        clash_bin = _clash_bin

        def init_worker():
            signal.signal(signal.SIGINT, signal.SIG_IGN)

        splitted_proxies = designate_jobs(self.proxies, os.cpu_count() + 1)
        picker = get_tcp_port_picker()
        ports = [next(picker) for _ in range(2 * len(splitted_proxies))]
        splitted_ports = designate_jobs(ports, len(splitted_proxies))
        logging.info('Update egress IP')
        try:
            pool = multiprocessing.Pool(len(splitted_proxies), init_worker)
            splitted_proxies_r = pool.starmap(
                worker_egress, zip(splitted_proxies, splitted_ports)
            )
            pool.close()
            pool.join()
        except KeyboardInterrupt:
            pool.terminate()
            pool.join()
            sys.exit(1)

        # value feed back
        proxies = []
        for proxy_group in splitted_proxies_r:
            proxies += proxy_group
        for src, dst in zip(proxies, self.proxies):
            dst.egress_ip = src.egress_ip

    def __getitem__(self, key):
        return self.data[key]

    def __iter__(self) -> Iterator[SubscriptionConfig]:
        return iter(self.data)
