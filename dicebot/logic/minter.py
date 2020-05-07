import logging

from mintersdk.minterapi import MinterAPI
from mintersdk.sdk.transactions import MinterSendCoinTx, MinterMultiSendCoinTx
from mintersdk.sdk.wallet import MinterWallet
from requests import ReadTimeout, ConnectTimeout, HTTPError

from dice_time.settings import NODE_API_URL, LOCAL, LOCAL_REAL_TXS
from dicebot.logic.helpers import retry

logger = logging.getLogger('DiceMinter')


class MinterRetryAPI(MinterAPI):
    to_handle = ReadTimeout, ConnectTimeout, ConnectionError, HTTPError, ValueError, KeyError

    @retry(to_handle, tries=3, delay=0.5, backoff=2)
    def _request(self, command, request_type='get', **kwargs):
        return super()._request(command, request_type=request_type, **kwargs)


API = MinterRetryAPI(NODE_API_URL)


def find_gas_coin(address):
    balances = API.get_balance(address, pip2bip=True)['result']['balance']
    gas_coin = 'BIP'
    if balances['BIP'] < 0.01 and len(balances) > 1:
        for coin, balance in balances.items():
            if coin == 'BIP':
                continue
            if (balance - estimate_custom_send_fee(coin)) < 0:
                continue
            return coin
        gas_coin = None
    return gas_coin


def estimate_custom_send_fee(coin):
    wallet = MinterWallet.create()
    send_tx = MinterSendCoinTx(coin, wallet['address'], 0, nonce=0, gas_coin=coin)
    send_tx.sign(wallet['private_key'])
    return API.estimate_tx_commission(send_tx.signed_tx, pip2bip=True)['result']['commission']


def coin_convert(coin, amount, to):
    if coin == to:
        return amount
    result = API.estimate_coin_sell(coin, amount, to, pip2bip=True)['result']
    return float(result['will_get'])


def coin_send(private_key, addr_from, addr_to, coin, value, gas_coin='BIP', payload=''):
    logger.info(f'Sending: {value} {coin} -> {addr_to}')
    if LOCAL and not LOCAL_REAL_TXS:
        return {}
    nonce = API.get_nonce(addr_from)
    send_tx = MinterSendCoinTx(
        coin,
        addr_to,
        value,
        nonce=nonce,
        gas_coin=gas_coin,
        payload=payload)
    send_tx.sign(private_key)
    r = API.send_transaction(send_tx.signed_tx)
    logger.info(f'Send TX response:\n{r}')
    return r


def coin_multisend(private_key, address_from, multisend_list, gas_coin='BIP', payload=''):
    for send_rec in multisend_list:
        logger.info(f"Sending: {send_rec['value']} {send_rec['coin']} -> {send_rec['to']}")
    if LOCAL and not LOCAL_REAL_TXS:
        return {}
    nonce = API.get_nonce(address_from)
    tx = MinterMultiSendCoinTx(multisend_list, nonce=nonce, gas_coin=gas_coin, payload=payload)
    tx.sign(private_key)
    r = API.send_transaction(tx.signed_tx)
    logger.info(f'Send TX response:\n{r}')
    return r
