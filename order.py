import uuid
import requests
import datetime
import base64
from urllib.parse import urlparse
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# Assumes you have the authentication code from the prerequisites

API_KEY_ID = 'f0a3b857-6186-40dd-9c8d-4beb3a9148d8'
PRIVATE_KEY_PATH = './CBB-demo.txt'
BASE_URL = 'https://external-api.demo.kalshi.co/trade-api/v2'

def load_private_key(key_path):
    with open(key_path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())

def create_signature(private_key, timestamp, method, path):
    """Create the request signature with the key's algorithm."""
    # Strip query parameters before signing
    path_without_query = path.split('?')[0]
    message = f"{timestamp}{method}{path_without_query}".encode('utf-8')
    if isinstance(private_key, Ed25519PrivateKey):
        signature = private_key.sign(message)
    else:
        signature = private_key.sign(
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
            hashes.SHA256()
        )
    return base64.b64encode(signature).decode('utf-8')

# Add POST function to your existing auth code
def post(private_key, api_key_id, path, data, base_url=BASE_URL):
    """Make an authenticated POST request to the Kalshi API."""
    timestamp = str(int(datetime.datetime.now().timestamp() * 1000))
    # Signing requires the full URL path from root (e.g. /trade-api/v2/portfolio/events/orders)
    sign_path = urlparse(base_url + path).path
    signature = create_signature(private_key, timestamp, "POST", sign_path)

    headers = {
        'KALSHI-ACCESS-KEY': api_key_id,
        'KALSHI-ACCESS-SIGNATURE': signature,
        'KALSHI-ACCESS-TIMESTAMP': timestamp,
        'Content-Type': 'application/json'
    }

    return requests.post(base_url + path, headers=headers, json=data)

# Step 1: Find an open market
print("Finding an open market...")
response = requests.get('https://external-api.demo.kalshi.co/trade-api/v2/markets?limit=1&status=open&series_ticker=KXNBAGAME')
market = response.json()['markets'][0]
print(f"Selected: {market['ticker']} - {market['title']}")

# Step 2: Place a buy order
print("\nPlacing order...")
client_order_id = str(uuid.uuid4())
order_data = {
    "ticker": market['ticker'],
    "side": "bid",
    "count": "1.00",
    "price": "0.4400",
    "time_in_force": "good_till_canceled",
    "self_trade_prevention_type": "taker_at_cross",
    "client_order_id": client_order_id,
    "post_only": False,
    "cancel_order_on_pause": False,
    "reduce_only": False,
    "subaccount": 0,
    "exchange_index": -1
}

# Load private key
private_key = load_private_key(PRIVATE_KEY_PATH)

response = post(private_key, API_KEY_ID, '/portfolio/events/orders', order_data)

if response.status_code == 201:
    order = response.json()
    print(f"Order placed successfully!")
    print(f"Order ID: {order['order_id']}")
    print(f"Client Order ID: {client_order_id}")
    print(f"Remaining Count: {order['remaining_count']}")
else:
    print(f"Error: {response.status_code} - {response.text}")