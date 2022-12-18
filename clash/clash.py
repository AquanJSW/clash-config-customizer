import json
import logging
import time
import os
import subprocess
import tempfile

import requests
from config.config import Config

import yaml


class Clash:
    def __init__(self, bin: str, config: Config) -> None:
        self.bin = bin
        self.config = config
        self._config_name = self._dump_config()
        self._log_fd = tempfile.SpooledTemporaryFile()
        self._start()
        self._requested_switch_count = 0
        self._success_switch_count = 0

    def switch_proxy(self, proxy_name: str):
        self._requested_switch_count += 1
        payload = {'name': proxy_name}
        ret = False
        try:
            r = requests.put(
                url=self.config.controller + '/proxies/GLOBAL',
                data=json.dumps(payload),
                timeout=1,
            )
            if r.status_code == 204:
                self._success_switch_count += 1
                ret = True
        except:
            ret = False
        if len(self.config.proxies) == self._requested_switch_count:
            if self._success_switch_count == 0:
                logging.warning(f'[clash] no successful switching')
                self._print_log()
        return ret

    def _start(self):
        logging.info(
            f'[clash] new clash, '
            f'{len(self.config.proxies)} proxies, '
            f'config is {self._config_name}'
        )
        self._proc = subprocess.Popen(
            f'{self.bin} -f {self._config_name}'.split(' '),
            stdout=self._log_fd,
            stderr=self._log_fd,
        )
        time.sleep(3)

    def _dump_config(self):
        fd = tempfile.NamedTemporaryFile('w', encoding='utf-8', delete=False)
        yaml.safe_dump(self.config.data, fd, allow_unicode=True)
        fd.close()
        return fd.name

    def _print_log(self):
        self._proc.kill()
        self._log_fd.seek(0)
        log = ''.join([str(b, encoding='utf-8') for b in self._log_fd.readlines()])
        logging.debug('Clash log')
        logging.debug(log)

    def __del__(self):
        try:
            self._proc.kill()
        except:
            pass

        try:
            os.remove(self._config_name)
        except Exception as e:
            logging.warning(
                f'Failed to delete temporary Clash config "{self._config_name}", '
                f'error type {type(e)}'
            )
