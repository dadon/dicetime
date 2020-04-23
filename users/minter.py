import logging

from django.conf import settings
from mintersdk.minterapi import MinterAPI

from mintersdk.sdk.transactions import MinterSendCoinTx, MinterMultiSendCoinTx
from requests import ReadTimeout, ConnectTimeout, HTTPError

from dice_time.settings import LOCAL, LOCAL_REAL_TXS
from users.tools import retry

logger = logging.getLogger('DiceMinter')


class MinterRetryAPI(MinterAPI):
    to_handle = ReadTimeout, ConnectTimeout, ConnectionError, HTTPError, ValueError, KeyError

    @retry(to_handle, tries=3, delay=0.5, backoff=2)
    def _request(self, command, request_type='get', **kwargs):
        return super()._request(command, request_type=request_type, **kwargs)


API = MinterRetryAPI(settings.NODE_API_URL)


def send(wallet_from, wallet_to, coin, value, gas_coin='BIP', payload=''):
    logger.info(f'Sending: {value} {coin} -> {wallet_to}')
    if LOCAL and not LOCAL_REAL_TXS:
        return {}
    nonce = API.get_nonce(wallet_from['address'])
    send_tx = MinterSendCoinTx(
        coin,
        wallet_to,
        value,
        nonce=nonce,
        gas_coin=gas_coin,
        payload=payload)
    send_tx.sign(wallet_from['private_key'])
    r = API.send_transaction(send_tx.signed_tx)
    logger.info(f'Send TX response:\n{r}')
    return r


def multisend(wallet_from, w_dict, gas_coin='BIP', payload=''):
    for send_rec in w_dict:
        logger.info(f"Sending: {send_rec['value']} {send_rec['coin']} -> {send_rec['to']}")
    if LOCAL and not LOCAL_REAL_TXS:
        return {}

    nonce = API.get_nonce(wallet_from['address'])
    tx = MinterMultiSendCoinTx(w_dict, nonce=nonce, gas_coin=gas_coin, payload=payload)
    tx.sign(wallet_from['private_key'])
    r = API.send_transaction(tx.signed_tx)
    logger.info(f'Send TX response:\n{r}')
    return r


def wallet_balance(address, with_nonce=False):
    response = API.get_balance(address, pip2bip=True)
    logging.debug(f'{address} balance response: {response}')
    balance = response['result']['balance']
    nonce = response['result']['transaction_count'] + 1
    return (balance, nonce) if with_nonce else balance


def coin_convert(coin, amount, to):
    if coin == to:
        return amount
    result = API.estimate_coin_sell(coin, amount, to, pip2bip=True)['result']
    return float(result['will_get'])
