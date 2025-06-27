How the `simulate_order_cron.py` simulation works, including what happens at each stage, how order failures and retries are handled, and the logic behind each decision.

---

## **Simulation Logic Overview**

### Goal

Simulate how a backend system handles **order creation**, including:

* Hourly job (cron) that attempts to process orders
* Failures due to simulated timeouts
* Retry logic with exponential backoff
* Maximum retry limit to avoid infinite loops
* Final reporting of outcomes

---

## **Execution Flow**

### 1. **Initialization**

* Total simulation runs for `SIMULATION_HOURS = 48`
* Time moves forward in hourly steps (`CRON_INTERVAL_HOURS = 1`)
* Two key queues:

  * `order_queue`: orders waiting to be (re)processed
  * `order_log`: history of every attempt for auditing

---

### 2. **Order Ingestion (Import)**

* At defined hours (`IMPORT_SCHEDULE`), new orders are generated
* Each order has:

  * A unique `order_id`
  * Status (`queued`, `created`, `failed`)
  * Retry count
  * `next_retry_at` timestamp (used to simulate backoff timing)

```python
"status": "queued",
"retries": 0,
"next_retry_at": current_time
```

---

### 3. **Order Processing (Cron Job Simulation)**

Every simulated hour, a function `process_orders()` is called.

This does:

* Loops through the `order_queue`
* Skips any order that is not yet eligible (`next_retry_at > current_time`)
* Tries to simulate the API call (`simulate_order_create()`)

---

### 4. **Simulating API Behavior**

The call `simulate_order_create()` randomly does one of:

* `Success` (\~40% chance)
* `Timeout` (\~60% chance), simulating network/API failure

---

### 5. **Handling Failures**

If timeout occurs:

* Increase the retry count
* If retry count is under `MAX_RETRIES`, compute a **simulated backoff delay**:

```python
order["next_retry_at"] = current_time + exponential_delay(order["retries"])
```

This simulates delays like:

* Retry 1 → wait 5 min

* Retry 2 → wait 10 min

* Retry 3 → wait 20 min

* Capped at 60 minutes

* If retries exceed `MAX_RETRIES`, mark order as `"failed"` and stop retrying

---

### 6. **Logging & Tracking**

Each attempt is logged:

```python
order_log.append(order.copy())
```

It stores full details of:

* `order_id`
* `status`
* `retries`
* `last_attempt`
* `created_at`

This helps in:

* Debugging logic
* Auditing final outcome
* Performance review

---

### 7. **End of Simulation**

After 48 simulated hours:

* Summarize all results:

  * Total successful orders
  * Total failed (after max retries)
  * Orders still queued for retry (not yet eligible by timestamp)
  * Total number of attempts across all orders

---

## **Design Reasoning**

| Component         | Purpose                                                 |
| ----------------- | ------------------------------------------------------- |
| `order_queue`     | Pending orders, live retry scheduling                   |
| `retry count`     | Prevents infinite retries                               |
| `next_retry_at`   | Simulates exponential backoff over time                 |
| `order_log`       | Audit trail and stats                                   |
| `IMPORT_SCHEDULE` | Mimics business load variations (e.g. peak hour bursts) |
| `random()` logic  | Models real-world API instability                       |

---

## Summary of Behaviors

| Scenario                           | System Response                       |
| ---------------------------------- | ------------------------------------- |
| Order succeeds                     | Mark as `"created"`, log it, done.    |
| Order times out, under retry limit | Retry later using backoff.            |
| Order times out, hits retry limit  | Mark as `"failed"`, no more attempts. |
| Order not due yet                  | Leave in queue until `next_retry_at`. |

---

## What This Simulates Accurately

* Realistic order submission failure rates
* How cron-based retry queues can get overwhelmed
* How backlog affects retry timing
* That *timeouts don’t mean failure* — they require smart retry logic

---
