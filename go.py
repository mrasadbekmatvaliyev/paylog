import requests
from concurrent.futures import ThreadPoolExecutor

URL = "http://127.0.0.1:8000/api/v1/debtors/"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzcwMzEyOTExLCJpYXQiOjE3Njk4ODA5MTEsImp0aSI6ImRiOWM3ZGYwODRiZTQyNTBhM2QxZjNiNzg4Njg2NzIxIiwidXNlcl9pZCI6IjE1In0.2VApao88-Qe9go3Xs2tdHMH-hnMMDuXO4J3knyW-KDw"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

base_phone = 998900000000

def send(i):
    payload = {
        "full_name": f"Stress User {i}",
        "phone": str(base_phone + i)
    }
    r = requests.post(URL, json=payload, headers=HEADERS)
    return r.status_code

USERS = 2000
WORKERS = 10  # 10 parallel request

with ThreadPoolExecutor(max_workers=WORKERS) as executor:
    for status in executor.map(send, range(1, USERS + 1)):
        print(status)
