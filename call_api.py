import time
import requests


def call(url: str, headers: dict, params: dict = None) -> list:
    response = requests.get(url=url, headers=headers, params=params)

    # Wait and retry if Rate limit for API exceeded
    while response.status_code == 429:
        time.sleep(1)
        response = requests.get(url, headers=headers, params=params)

    # Success
    if response.status_code == 200:
        return response.json()
