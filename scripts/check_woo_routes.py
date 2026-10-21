
import os
import requests
from dotenv import load_dotenv
from requests_oauthlib import OAuth1

load_dotenv()

store_url = os.environ["WOOCOMMERCE_URL"].rstrip("/")
auth = OAuth1(
    os.environ["WOOCOMMERCE_CONSUMER_KEY"],
    client_secret=os.environ["WOOCOMMERCE_CONSUMER_SECRET"],
    signature_method="HMAC-SHA1",
)

endpoints = [
    "/wp-json/",
    "/wp-json/wc/v3/",
    "/wp-json/wc/v3/products?per_page=1",
    "/wp-json/wc/v3/orders?per_page=1",
]

for endpoint in endpoints:
    try:
        response = requests.get(
            store_url + endpoint,
            auth=auth,
            timeout=15,
        )
        print(f"\n{endpoint}")
        print("HTTP:", response.status_code)
        print("Content-Type:", response.headers.get("Content-Type"))
        print("Response:", response.text[:250].replace("\n", " "))
    except requests.RequestException as exc:
        print(f"\n{endpoint}")
        print("Request failed:", type(exc).__name__, str(exc))
