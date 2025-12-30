import requests

BASE = "https://abdi-kundendaten-default-rtdb.europe-west1.firebasedatabase.app"

def load_json(path: str):
    url = f"{BASE}/{path}.json"
    response = requests.get(url)
    if response.status_code == 200 and response.json() is not None:
        return response.json()
    return []

def save_json(path: str, data):
    url = f"{BASE}/{path}.json"
    requests.put(url, json=data)
