"""Coinbase Advanced API integration module."""

from app.modules.coinbase.client import CoinbaseClient
from app.modules.coinbase.service import CoinbaseService


__all__ = ["CoinbaseClient", "CoinbaseService"]
