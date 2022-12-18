from typing import MutableMapping, Union
from ipaddress import IPv4Address, IPv6Address
import geoip2.models


class Proxy:
    def __init__(self, data: MutableMapping) -> None:
        self.data = data
        self.ingress_ip: Union[IPv4Address, IPv6Address, None] = None
        self.egress_ip: Union[IPv4Address, IPv6Address, Exception, None] = None
        self.geometry: Union[geoip2.models.Country, None] = None

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __str__(self):
        return (
            f'name: {self["name"]}\n'
            f'server: {self["server"]}\n'
            f'ingress: {self.ingress_ip}\n'
            f'egress: {self.egress_ip}'
        )

    def __hash__(self):
        """

        Return
        ---
        `0` for invalid proxies, `non-0` for the others.
        """
        val = 0
        if (
            isinstance(self.ingress_ip, IPv4Address)
            or isinstance(self.ingress_ip, IPv6Address)
        ) and (
            isinstance(self.egress_ip, IPv4Address)
            or isinstance(self.egress_ip, IPv6Address)
        ):
            val = hash(str(self.ingress_ip) + str(self.egress_ip))
        return val

    def __eq__(self, __o: object) -> bool:
        assert isinstance(__o, Proxy)
        return hash(self) == hash(__o)
