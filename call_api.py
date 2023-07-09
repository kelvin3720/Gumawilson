import time
import requests


def call(url: str, headers: dict, params: dict = None) -> list:
    """Call api, will wait if rate limit exceeded"""
    response = requests.get(url=url, headers=headers, params=params)

    while response.status_code == 429:
        time.sleep(1)
        response = requests.get(url, headers=headers, params=params)

    # Success
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error: {str(response.status_code)}")
