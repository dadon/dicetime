import requests


def get_user_timeloop_address(user_id):
    r = requests.get(f'https://timeloop.games/bot-status/{user_id}')
    if r.status_code != 200:
        return None
    return r.json().get('address')
