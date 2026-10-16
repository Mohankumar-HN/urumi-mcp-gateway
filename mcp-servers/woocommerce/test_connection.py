
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

url = os.environ["WOOCOMMERCE_URL"].rstrip("/")
key = os.environ["WOOCOMMERCE_CONSUMER_KEY"]
secret = os.environ["WOOCOMMERCE_CONSUMER_SECRET"]
print("Store URL:", url)
print("Consumer key loaded:", bool(key))
print("Consumer secret loaded:", bool(secret))

try:
    response = httpx.get(
        f"{url}/wp-json/wc/v3/products",
        params={"per_page": 5},
        auth=(key, secret),
        timeout=15,
    )

    print("HTTP status:", response.status_code)

    if response.is_success:
        print("WooCommerce API connection successful!")
        for product in response.json():
            print(
                f"Product: {product.get('name')} | "
                f"Price: {product.get('price')}"
            )
    else:
        print("Response:", response.text[:1000])

except Exception as exc:
    print("Connection failed:", type(exc).__name__, str(exc))
