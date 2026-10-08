"""Tiny Alpaca client. Paper only: config.get_base_url() refuses anything else."""
import requests
from config import get_keys, get_base_url


class Alpaca:
    def __init__(self):
        key, secret = get_keys()
        self.base = get_base_url()
        self.h = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}

    def _get(self, path):
        r = requests.get(self.base + path, headers=self.h, timeout=20)
        r.raise_for_status()
        return r.json()

    def account(self):
        return self._get("/v2/account")

    def positions(self):
        return self._get("/v2/positions")
