
import os
import requests
from dotenv import load_dotenv
from requests_oauthlib import OAuth1

load_dotenv()

url = os.environ["WOOCOMMERCE_URL"].rstrip("/")
key = os.environ["WOOCOMMERCE_CONSUMER_KEY"]
secret = os.environ["WOOCOMMERCE_CONSUMER_SECRET"]

auth = OAuth1(
    key,
    client_secret=secret,
    signature_method="HMAC-SHA1",
)

response = requests.get(
    f"{url}/wp-json/wc/v3/products",
    params={"per_page": 5},
    auth=auth,
    timeout=15,
)

print("HTTP status:", response.status_code)
print("Response:", response.text[:1000])
