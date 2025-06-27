import sqlite3
from datetime import datetime, timedelta
import random
import time
from pathlib import Path

DB_PATH = Path("orders.db")
MAX_RETRIES = 5
MAX_RETRY_PER_CRON = 20
MAX_QUEUE_SIZE_BEFORE_THROTTLE = 100
SIMULATION_HOURS = 48
CRON_INTERVAL_HOURS = 1

IMPORT_SCHEDULE = {
    0: 5,
    4: 10,
    8: 20,
    12: 50,
    18: 30,
    24: 60,
    36: 40
}

def now():
    return datetime.now().isoformat(sep=' ', timespec='seconds')

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            status TEXT,
            retries INTEGER,
            created_at TEXT,
            last_attempt TEXT,
            next_retry_at TEXT
        )
        """)
        conn.commit()

def add_orders(n, current_time):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        for i in range(n):
            order_id = f"ORD-{int(current_time.timestamp())}-{random.randint(1000,9999)}"
            c.execute("""
                INSERT INTO orders (order_id, status, retries, created_at, last_attempt, next_retry_at)
                VALUES (?, 'queued', 0, ?, NULL, ?)
            """, (order_id, current_time.isoformat(sep=' ', timespec='seconds'),
                  current_time.isoformat(sep=' ', timespec='seconds')))
        conn.commit()

def simulate_order_create():
    rand = random.random()
    if rand < 0.6:
        raise TimeoutError("Simulated timeout")
    return "created"

def exponential_delay(retries):
    return timedelta(minutes=min(60, 2 ** retries * 5))

def process_orders(current_time):
    processed, success, failed, rescheduled = 0, 0, 0, 0
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT * FROM orders
            WHERE status = 'queued' AND next_retry_at <= ?
            ORDER BY retries ASC, created_at ASC
            LIMIT ?
        """, (current_time.isoformat(sep=' ', timespec='seconds'), MAX_RETRY_PER_CRON))
        orders = c.fetchall()

        for order in orders:
            processed += 1
            try:
                simulate_order_create()
                c.execute("UPDATE orders SET status = 'created', last_attempt = ? WHERE order_id = ?",
                          (current_time.isoformat(sep=' ', timespec='seconds'), order["order_id"]))
                success += 1
            except TimeoutError:
                new_retries = order["retries"] + 1
                if new_retries >= MAX_RETRIES:
                    c.execute("UPDATE orders SET status = 'failed', retries = ?, last_attempt = ? WHERE order_id = ?",
                              (new_retries, current_time.isoformat(sep=' ', timespec='seconds'), order["order_id"]))
                    failed += 1
                else:
                    next_retry = current_time + exponential_delay(new_retries)
                    c.execute("""
                        UPDATE orders
                        SET retries = ?, last_attempt = ?, next_retry_at = ?
                        WHERE order_id = ?
                    """, (new_retries, current_time.isoformat(sep=' ', timespec='seconds'),
                          next_retry.isoformat(sep=' ', timespec='seconds'), order["order_id"]))
                    rescheduled += 1
        conn.commit()
    return processed, success, failed, rescheduled

def get_queued_order_count():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM orders WHERE status = 'queued'")
        return c.fetchone()[0]

def simulate_cron():
    init_db()
    current_time = datetime.now()

    for hour in range(SIMULATION_HOURS):
        current_time += timedelta(hours=CRON_INTERVAL_HOURS)
        print(f"\n[{current_time.strftime('%Y-%m-%d %H:%M')}] Cron triggered")

        queued_count = get_queued_order_count()
        if hour in IMPORT_SCHEDULE:
            if queued_count < MAX_QUEUE_SIZE_BEFORE_THROTTLE:
                add_orders(IMPORT_SCHEDULE[hour], current_time)
                print(f"[{current_time.strftime('%H:%M')}] Imported {IMPORT_SCHEDULE[hour]} new orders.")
            else:
                print(f"[{current_time.strftime('%H:%M')}] Skipped import (queue size = {queued_count})")

        processed, success, failed, rescheduled = process_orders(current_time)
        print(f"[{current_time.strftime('%H:%M')}] Processed: {processed}, "
              f"Success: {success}, Failed: {failed}, Rescheduled: {rescheduled}")
        time.sleep(0.3)

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM orders WHERE status = 'created'")
        success_total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM orders WHERE status = 'failed'")
        failed_total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM orders WHERE status = 'queued'")
        remaining_total = c.fetchone()[0]

    print("\n--- SIMULATION COMPLETE ---")
    print(f"Success: {success_total}")
    print(f"Failed: {failed_total}")
    print(f"Still queued: {remaining_total}")

if __name__ == '__main__':
    simulate_cron()
