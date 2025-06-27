import time
import random
import json
import requests
import logging
from datetime import datetime
from pathlib import Path

RETRY_FILE = Path("retry_queue.json")
LOG_FILE = Path("order_post.log")
SIMULATED_ORDER_STORE = set()
MAX_RETRIES = 5
BASE_DELAY = 1
MAX_DELAY = 16

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def current_time():
    return datetime.now().strftime("%H:%M:%S")

def get_order_reference():
    return f"ORDER-{int(time.time())}"

def simulate_make_request(order_reference):
    rand = random.random()
    if rand < 0.5:
        raise requests.exceptions.Timeout("Simulated timeout.")
    elif rand < 0.7:
        SIMULATED_ORDER_STORE.add(order_reference)
        raise requests.exceptions.Timeout("Timeout, but order was created.")
    elif rand < 0.9:
        if order_reference in SIMULATED_ORDER_STORE:
            return "Duplicate order"
        else:
            SIMULATED_ORDER_STORE.add(order_reference)
            return "Success!"
    else:
        SIMULATED_ORDER_STORE.add(order_reference)
        return "Success!"

def check_if_order_exists(order_reference):
    return order_reference in SIMULATED_ORDER_STORE

def persist_retry(order_reference, status, retries):
    retry_data = {
        "order_reference": order_reference,
        "status": status,
        "retries": retries,
        "last_attempt": datetime.now().isoformat()
    }
    RETRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if RETRY_FILE.exists():
        try:
            with open(RETRY_FILE, "r") as f:
                existing = json.load(f)
        except json.JSONDecodeError:
            pass
    existing.append(retry_data)
    with open(RETRY_FILE, "w") as f:
        json.dump(existing, f, indent=2)
    logging.warning(f"Order {order_reference} added to retry queue after {retries} retries.")

def exponential_backoff_request(order_reference, max_retries=MAX_RETRIES, base_delay=BASE_DELAY, max_delay=MAX_DELAY):
    retries = 0
    while retries < max_retries:
        try:
            print(f"[{current_time()}] Sending order: {order_reference}")
            result = simulate_make_request(order_reference)
            print(f"[{current_time()}] Request succeeded: {result}")
            logging.info(f"Order {order_reference} succeeded with result: {result}")
            return result
        except requests.exceptions.Timeout as e:
            print(f"[{current_time()}] Timeout: {e}")
            logging.warning(f"Timeout for order {order_reference}, attempt {retries + 1}")
            if check_if_order_exists(order_reference):
                print(f"[{current_time()}] Order confirmed created despite timeout.")
                logging.info(f"Order {order_reference} created despite timeout.")
                return "Success after timeout"
            wait_time = min(base_delay * (2 ** retries), max_delay)
            print(f"[{current_time()}] ⏳ Retrying in {wait_time:.1f} seconds... (Attempt {retries + 1}/{max_retries})")
            time.sleep(wait_time)
            retries += 1

    print(f"[{current_time()}] ❌ All retries failed. Final check...")
    if check_if_order_exists(order_reference):
        print(f"[{current_time()}] Order confirmed created after all retries.")
        logging.info(f"Order {order_reference} confirmed created after max retries.")
        return "Success after timeout"

    persist_retry(order_reference, status="unknown", retries=retries)
    print(f"[{current_time()}] Order failed. Added to retry queue.")
    return None

if __name__ == "__main__":
    order_ref = get_order_reference()
    result = exponential_backoff_request(order_ref)
    print(f"\nFinal result: {result}")
