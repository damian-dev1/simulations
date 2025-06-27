import time
import random
import requests
from datetime import datetime, timedelta

# Simulated backend store (for idempotent order reference tracking)
SIMULATED_ORDER_STORE = set()

def current_time():
    return datetime.now().strftime("%H:%M:%S")

def make_request(order_reference):
    outcome = random.random()
    if outcome < 0.5:
        raise requests.exceptions.Timeout("Simulated timeout.")
    elif outcome < 0.7:
        # Simulate timeout, but order was actually created
        SIMULATED_ORDER_STORE.add(order_reference)
        raise requests.exceptions.Timeout("Timeout, but order was created.")
    elif outcome < 0.9:
        # Simulate duplicate order
        if order_reference in SIMULATED_ORDER_STORE:
            return "Duplicate order"
        else:
            SIMULATED_ORDER_STORE.add(order_reference)
            return "Success!"
    else:
        # Successful order
        SIMULATED_ORDER_STORE.add(order_reference)
        return "Success!"

def check_if_order_exists(order_reference):
    return order_reference in SIMULATED_ORDER_STORE

def exponential_backoff_request(order_reference, max_retries=5, base_delay=1.0, max_delay=16.0):
    retries = 0
    while retries < max_retries:
        try:
            print(f"[{current_time()}] Sending order: {order_reference}")
            result = make_request(order_reference)
            print(f"[{current_time()}] Request succeeded: {result}")
            return result
        except requests.exceptions.Timeout as e:
            print(f"[{current_time()}] ⚠️ Timeout occurred: {e}")
            if check_if_order_exists(order_reference):
                print(f"[{current_time()}] Order confirmed created despite timeout.")
                return "Success after timeout"
            wait_time = min(base_delay * (2 ** retries), max_delay)
            print(f"[{current_time()}] ⏳ Retrying in {wait_time:.1f} seconds... (Attempt {retries + 1}/{max_retries})")
            time.sleep(wait_time)
            retries += 1

    if check_if_order_exists(order_reference):
        print(f"[{current_time()}] Order confirmed created after max retries.")
        return "Success after timeout"
    else:
        print(f"[{current_time()}] ❌ All retries failed. Giving up.")
        return None

if __name__ == "__main__":
    order_ref = f"ORDER-{int(time.time())}"
    result = exponential_backoff_request(order_ref)
    print(f"\nFinal result: {result}")
