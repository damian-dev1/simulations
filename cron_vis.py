import time
import random
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

CRON_INTERVAL_HOURS = 1
SIMULATION_HOURS = 48

# Custom Import Schedule (Hour -> SKU Count)
IMPORT_SCHEDULE = {
    0: 1000,
    3: 3000,
    6: 5000,
    12: 20000,
    18: 8000,
    24: 12000,
    36: 15000
}

sku_queue = 0
time_now = datetime.now()
cron_run_log = []
backlog_history = []  # Stores backlog sizes over time
processing_history = []  # Stores processed SKUs per run
import_history = []  # Stores imported SKUs per run
timestamps = []  # Stores timestamps for graphing

def get_dynamic_batch_size(backlog_size):
    """Dynamically determines batch size based on backlog"""
    if backlog_size < 5000:
        return 500
    elif backlog_size < 10000:
        return 1000
    elif backlog_size < 50000:
        return 2500
    else:
        return 5000

def import_skus(count):
    """Simulates SKU import"""
    global sku_queue
    sku_queue += count
    import_history.append(count)
    print(f"[{time_now.strftime('%Y-%m-%d %H:%M:%S')}] 📥 Imported {count} SKUs. Total backlog: {sku_queue}")
    
def run_cron():
    """Simulates Magento cron job with dynamic batch processing"""
    global sku_queue
    batch_size = get_dynamic_batch_size(sku_queue)
    processed = min(batch_size, sku_queue)
    sku_queue -= processed
    processing_history.append(processed)
    print(f"[{time_now.strftime('%Y-%m-%d %H:%M:%S')}] ✅ Processed {processed} SKUs. Remaining: {sku_queue}")

for hour in range(SIMULATION_HOURS):
    time_now += timedelta(hours=CRON_INTERVAL_HOURS)
    timestamps.append(time_now)

    # Import SKUs if the current hour matches the import schedule
    if hour in IMPORT_SCHEDULE:
        import_skus(IMPORT_SCHEDULE[hour])
    else:
        import_history.append(0)  # No import at this hour

    # Run cron job every hour
    run_cron()
    backlog_history.append(sku_queue)
    time.sleep(0.2)  # Simulate real-time processing

# Create DataFrame for visualization
df = pd.DataFrame({
    'Time': timestamps,
    'Backlog': backlog_history,
    'Processed': processing_history,
    'Imported': import_history
})

# Plot backlog trends
plt.figure(figsize=(12, 5))
plt.plot(df['Time'], df['Backlog'], marker='o', linestyle='-', label='Backlog Size')
plt.xlabel('Time')
plt.ylabel('SKU Backlog')
plt.title('SKU Backlog Over Time')
plt.legend()
plt.xticks(rotation=45)
plt.grid(True)
plt.show()

# Bar chart for processed/imported SKUs
plt.figure(figsize=(12, 5))
plt.bar(df['Time'], df['Imported'], alpha=0.6, label='Imported SKUs', color='blue')
plt.bar(df['Time'], df['Processed'], alpha=0.6, label='Processed SKUs', color='green')
plt.xlabel('Time')
plt.ylabel('SKU Count')
plt.title('Imported vs Processed SKUs')
plt.legend()
plt.xticks(rotation=45)
plt.show()

# Heatmap for backlog intensity
plt.figure(figsize=(10, 4))
heatmap_data = pd.DataFrame({'Hour': range(SIMULATION_HOURS), 'Backlog': backlog_history})
heatmap_data = heatmap_data.pivot_table(index='Hour', values='Backlog')
sns.heatmap(heatmap_data, cmap='coolwarm', annot=True, fmt=".0f")
plt.title('Backlog Heatmap')
plt.xlabel('Hour')
plt.ylabel('Backlog Intensity')
plt.show()
