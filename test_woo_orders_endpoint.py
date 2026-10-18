
import os
import requests
from dotenv import load_dotenv
from requests_oauthlib import OAuth1

load_dotenv()

store_url = os.environ["WOOCOMMERCE_URL"].rstrip("/")
consumer_key = os.environ["WOOCOMMERCE_CONSUMER_KEY"]
consumer_secret = os.environ["WOOCOMMERCE_CONSUMER_SECRET"]

auth = OAuth1(
    consumer_key,
    client_secret=consumer_secret,
    signature_method="HMAC-SHA1",
)

url = f"{store_url}/wp-json/wc/v3/orders"

try:
    response = requests.get(
        url,
        params={"per_page": 1},
        auth=auth,
        timeout=15,
    )

    print("HTTP status:", response.status_code)
    print("Response:", response.text[:1500])

except requests.RequestException as exc:
    print("Request failed:", type(exc).__name__, str(exc))
