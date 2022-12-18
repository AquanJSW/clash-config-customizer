from typing import Mapping
from .config import Config


class SubscriptionConfig(Config):
    def __init__(self, data: Mapping, enable_rename: bool) -> None:
        super().__init__(data=data)
        self.enable_rename = enable_rename

    def add_prefix(self, prefix: str):
        for proxy in self.proxies:
            proxy['name'] = prefix + proxy['name']
