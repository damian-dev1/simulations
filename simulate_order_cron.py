import time
import random
from datetime import datetime, timedelta

# --- CONFIGURATION ---
SIMULATION_HOURS = 48
CRON_INTERVAL_HOURS = 1
MAX_RETRIES = 5
IMPORT_SCHEDULE = {
    0: 5,     # 00:00 - 5 orders
    4: 10,    # 04:00 - 10 orders
    8: 20,    # 08:00 - 20 orders
    12: 50,   # 12:00 - 50 orders
    18: 30,   # 18:00 - 30 orders
    24: 60,   # 24:00 - 60 orders
    36: 40    # 36:00 - 40 orders
}

# --- STATE ---
order_queue = []  # Orders pending submission
retry_queue = []  # Orders scheduled for retry with future timestamp
order_log = []
time_now = datetime.now()
order_id_counter = 0

def generate_orders(n, current_time):
    global order_id_counter
    new_orders = []
    for _ in range(n):
        order_id_counter += 1
        new_orders.append({
            "order_id": f"ORD-{order_id_counter}",
            "status": "queued",
            "created_at": current_time,
            "retries": 0,
            "next_retry_at": current_time
        })
    return new_orders

def simulate_order_create():
    rand = random.random()
    if rand < 0.6:
        raise TimeoutError("Simulated timeout")
    return "created"

def exponential_delay(retries):
    return timedelta(minutes=min(60, 2 ** retries * 5))  # 5, 10, 20... up to 60 min

def process_orders(current_time):
    global order_queue, retry_queue
    processed = 0
    success = 0
    failed = 0
    rescheduled = 0

    next_queue = []
    for order in order_queue:
        if order["next_retry_at"] > current_time:
            next_queue.append(order)
            continue

        processed += 1
        try:
            result = simulate_order_create()
            order["status"] = result
            success += 1
        except TimeoutError:
            order["retries"] += 1
            if order["retries"] >= MAX_RETRIES:
                order["status"] = "failed"
                failed += 1
            else:
                order["next_retry_at"] = current_time + exponential_delay(order["retries"])
                next_queue.append(order)
                rescheduled += 1

        order["last_attempt"] = current_time
        order_log.append(order.copy())

    order_queue = next_queue
    return processed, success, failed, rescheduled

# --- SIMULATION LOOP ---
for hour in range(SIMULATION_HOURS):
    time_now += timedelta(hours=CRON_INTERVAL_HOURS)

    if hour in IMPORT_SCHEDULE:
        new_orders = generate_orders(IMPORT_SCHEDULE[hour], time_now)
        order_queue.extend(new_orders)
        print(f"[{time_now.strftime('%Y-%m-%d %H:%M')}] Imported {len(new_orders)} orders")

    processed, success, failed, rescheduled = process_orders(time_now)
    print(f"[{time_now.strftime('%Y-%m-%d %H:%M')}] Processed: {processed}, "
          f"Success: {success}, Failed: {failed}, Rescheduled: {rescheduled}")

    time.sleep(0.2)

# --- FINAL SUMMARY ---
total = len(order_log)
succeeded = sum(1 for o in order_log if o["status"] == "created")
failed = sum(1 for o in order_log if o["status"] == "failed")
remaining = len(order_queue)

print("\n--- SIMULATION COMPLETE ---")
print(f"Success: {succeeded}")
print(f"Failed: {failed}")
print(f"Still queued for retry: {remaining}")
print(f"Total processed attempts: {total}")
