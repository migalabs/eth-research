import random
import numpy as np
import matplotlib.pyplot as plt

# Simulation parameters
NUM_SLOTS = 216000  # 30 days worth of slots
AVG_TX_PER_SLOT = 14  # Target average transactions per slot
MAX_TX_PER_SLOT = 21  # Maximum transactions per slot
NUM_SENDERS = 100  # Number of unique senders

# Skewness configuration: name -> decay rate (higher = more skewed)
SKEWNESS_CONFIG = {
    "very_high": 0.15,
    "high": 0.10,
    "medium_high": 0.07,
    "medium_low": 0.04,
    "low": 0.02,
    "uniform": 0.0,
}

def get_sender_distribution(num_senders, skewness):
    """Generate probability distribution for sender selection based on skewness."""
    x = np.arange(1, num_senders + 1)

    decay = SKEWNESS_CONFIG.get(skewness, 0.0)

    if decay == 0:
        probs = np.ones(num_senders)
    else:
        probs = np.exp(-decay * x)

    # Normalize to sum to 1
    return probs / probs.sum()

def generate_transaction_rate(num_slots, avg_tx_per_slot, max_tx_per_slot):
    """Generate time-varying transaction rate over the month.

    Creates a random, non-periodic rate pattern with:
    - Random base noise centered around the target average
    - Random bursts and lulls of varying intensity and duration
    - Capped at max_tx_per_slot per slot

    Returns actual transaction counts per slot (not probabilities).
    """
    # Start with random base rate centered around target average
    base_low = max(0, avg_tx_per_slot * 0.4)
    base_high = avg_tx_per_slot * 1.6
    rate = np.random.uniform(base_low, base_high, num_slots)

    # Add random bursts of activity
    num_bursts = 200
    for _ in range(num_bursts):
        burst_start = random.randint(0, num_slots - 1)
        burst_duration = random.randint(50, 2000)
        burst_end = min(burst_start + burst_duration, num_slots)
        burst_intensity = random.uniform(1.2, 2.0)
        rate[burst_start:burst_end] *= burst_intensity

    # Add random lulls (low activity periods)
    num_lulls = 100
    for _ in range(num_lulls):
        lull_start = random.randint(0, num_slots - 1)
        lull_duration = random.randint(100, 1500)
        lull_end = min(lull_start + lull_duration, num_slots)
        lull_intensity = random.uniform(0.3, 0.7)
        rate[lull_start:lull_end] *= lull_intensity

    # Cap at maximum transactions per slot
    rate = np.clip(rate, 0, max_tx_per_slot)

    # Round to integers
    tx_per_slot = np.round(rate).astype(int)

    # Scale to achieve target average (after capping)
    current_avg = tx_per_slot.mean()
    if current_avg > 0:
        scale_factor = avg_tx_per_slot / current_avg
        tx_per_slot = np.round(tx_per_slot * scale_factor).astype(int)
        tx_per_slot = np.clip(tx_per_slot, 0, max_tx_per_slot)

    return tx_per_slot

def generate_simulation_data():
    """Generate all transaction data for the simulation.

    Returns a dictionary containing:
    - tx_per_slot: transaction counts per slot
    - transaction_slots: slot index for each transaction
    - total_transactions: total number of transactions
    - sender_data: dict mapping skewness -> transaction_senders array
    """
    print("Generating transaction data...")

    # Generate transaction rate (shared across all skewness levels)
    tx_per_slot = generate_transaction_rate(NUM_SLOTS, AVG_TX_PER_SLOT, MAX_TX_PER_SLOT)
    total_transactions = tx_per_slot.sum()

    # Generate transaction slots by repeating slot index by tx count
    transaction_slots = np.repeat(np.arange(NUM_SLOTS), tx_per_slot)

    # Generate sender assignments for each skewness level
    sender_data = {}
    for skewness in SKEWNESS_CONFIG.keys():
        sender_probs = get_sender_distribution(NUM_SENDERS, skewness)
        transaction_senders = np.random.choice(NUM_SENDERS, size=total_transactions, p=sender_probs)
        sender_data[skewness] = transaction_senders

    print(f"  Total transactions: {total_transactions:,}")
    print(f"  Avg tx/slot: {tx_per_slot.mean():.2f}")

    return {
        'tx_per_slot': tx_per_slot,
        'transaction_slots': transaction_slots,
        'total_transactions': total_transactions,
        'sender_data': sender_data
    }

def simulate_nonce_gaps(num_shards, skewness, sim_data):
    """Simulate nonce gaps using pre-generated transaction data.

    Args:
        num_shards: Number of shards
        skewness: Skewness level key
        sim_data: Pre-generated simulation data from generate_simulation_data()

    Returns:
        Gap frequency (shard switches / total transactions)
    """
    transaction_slots = sim_data['transaction_slots']
    transaction_senders = sim_data['sender_data'][skewness]
    total_transactions = sim_data['total_transactions']

    # Assign random shard to each transaction
    transaction_shards = np.random.randint(0, num_shards, size=total_transactions)

    # Track last shard and slot for each sender and count gaps
    # Only count consecutive pairs that are in the SAME slot
    last_info = {}  # sender -> (last_shard, last_slot)
    shard_switches = 0

    for i in range(total_transactions):
        sender = transaction_senders[i]
        shard = transaction_shards[i]
        slot = transaction_slots[i]

        if sender in last_info:
            last_shard, last_slot = last_info[sender]
            # Only count if both transactions are in the same slot
            if slot == last_slot:
                if last_shard != shard:
                    shard_switches += 1

        last_info[sender] = (shard, slot)

    # Return frequency of shard switches out of ALL transactions
    if total_transactions == 0:
        return 0.0
    return shard_switches / total_transactions

def plot_distributions():
    """Plot probability distributions for all skewness levels."""
    x = np.arange(1, NUM_SENDERS + 1)

    plt.figure(figsize=(12, 6))

    for name, decay in SKEWNESS_CONFIG.items():
        if decay == 0:
            probs = np.ones(NUM_SENDERS) / NUM_SENDERS
        else:
            probs = np.exp(-decay * x)
            probs /= probs.sum()
        plt.plot(x, probs, label=name.replace('_', ' ').title(), marker='o', markersize=3)

    plt.xlabel('Sender Index (Ranked)')
    plt.ylabel('Probability')
    plt.title('Blob Transaction Frequency Distributions from Skewed to Uniform')
    plt.legend()
    plt.savefig('transaction_distribution.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: transaction_distribution.png")

def plot_transactions_per_sender(sim_data):
    """Plot the actual number of transactions per sender from simulation data."""
    plt.figure(figsize=(12, 6))

    for skewness in SKEWNESS_CONFIG.keys():
        transaction_senders = sim_data['sender_data'][skewness]

        # Count transactions per sender
        sender_counts = np.bincount(transaction_senders, minlength=NUM_SENDERS)

        # Sort by count (descending) to show ranked distribution
        sorted_counts = np.sort(sender_counts)[::-1]

        x = np.arange(1, NUM_SENDERS + 1)
        plt.plot(x, sorted_counts, label=skewness.replace('_', ' ').title(), marker='o', markersize=3)

    total_transactions = sim_data['total_transactions']
    avg_tx_per_slot = sim_data['tx_per_slot'].mean()

    plt.xlabel('Sender Index (Ranked by Transaction Count)')
    plt.ylabel('Number of Blob Transactions')
    plt.title(f'Blob Transactions per Sender ({total_transactions:,} total, {avg_tx_per_slot:.2f} avg/slot)')
    plt.legend()
    plt.savefig('transactions_per_sender.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: transactions_per_sender.png")

def plot_sender_distance_boxplot(sim_data):
    """Create a boxplot showing distribution of same-sender transaction distances (in slots)."""
    transaction_slots = sim_data['transaction_slots']
    total_transactions = sim_data['total_transactions']

    # Collect distances for each skewness level
    all_distances = []
    labels = []

    for skewness in SKEWNESS_CONFIG.keys():
        transaction_senders = sim_data['sender_data'][skewness]

        # Calculate distances between consecutive transactions from same sender
        last_slot = {}  # sender -> last slot
        distances = []

        for i in range(total_transactions):
            sender = transaction_senders[i]
            slot = transaction_slots[i]

            if sender in last_slot:
                distance = slot - last_slot[sender]
                distances.append(distance)

            last_slot[sender] = slot

        all_distances.append(distances)
        labels.append(skewness.replace('_', '\n'))

    # Create boxplot
    plt.figure(figsize=(12, 6))
    bp = plt.boxplot(all_distances, labels=labels, patch_artist=True)

    # Color the boxes
    colors = plt.cm.viridis(np.linspace(0, 0.8, len(labels)))
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    plt.xlabel('Skewness of Distribution')
    plt.ylabel('Distance Between Same-Sender Transactions (slots)')
    plt.title('Distribution of Same-Sender Transaction Distance')
    plt.ylim(0, 50)
    plt.grid(True, alpha=0.3, axis='y')
    plt.savefig('sender_distance_boxplot.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: sender_distance_boxplot.png")

def plot_transactions_over_time(sim_data):
    """Plot the number of transactions per hour as a bar chart."""
    tx_per_slot = sim_data['tx_per_slot']

    # Aggregate transactions per hour (300 slots per hour = 12 seconds per slot * 300 = 3600 seconds)
    slots_per_hour = 300
    num_hours = NUM_SLOTS // slots_per_hour

    tx_per_hour = np.zeros(num_hours)
    for h in range(num_hours):
        start_slot = h * slots_per_hour
        end_slot = start_slot + slots_per_hour
        tx_per_hour[h] = tx_per_slot[start_slot:end_slot].sum()

    # Create hour axis
    hours = np.arange(num_hours)

    plt.figure(figsize=(14, 6))

    # Bar plot
    plt.bar(hours, tx_per_hour, width=1.0, color='steelblue', edgecolor='none', alpha=0.8)

    # Calculate average transactions per slot
    avg_tx_per_slot = tx_per_slot.mean()

    plt.xlabel('Time (hours)')
    plt.ylabel('Transactions per Hour')
    plt.title(f'Blob Transaction Rate Over Time (30 days, avg {avg_tx_per_slot:.2f} tx/slot)')
    plt.xlim(0, num_hours)
    plt.ylim(0, MAX_TX_PER_SLOT * 300)  # Max capacity per hour
    plt.grid(True, alpha=0.3, axis='y')
    plt.savefig('transactions_over_time.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: transactions_over_time.png")

# =============================================================================
# Main simulation
# =============================================================================

# Generate all transaction data once
sim_data = generate_simulation_data()

# Define shard counts and skewness levels
shard_counts = [1, 2, 4, 8, 16, 32]
skewness_levels = list(SKEWNESS_CONFIG.keys())

# Create a heatmap data array
heatmap_data = np.zeros((len(shard_counts), len(skewness_levels)))

# Run the simulations
print("\nRunning nonce gap simulations...")
for i, num_shards in enumerate(shard_counts):
    for j, skewness in enumerate(skewness_levels):
        print(f"  Simulating: {num_shards} shards, {skewness} skewness...")
        gap_rate = simulate_nonce_gaps(num_shards, skewness, sim_data)
        heatmap_data[i, j] = gap_rate
        print(f"    -> Gap frequency: {gap_rate:.4f}")
print("Simulations complete.\n")

# Plot and save all distribution figures (using the same simulation data)
plot_distributions()
plot_transactions_per_sender(sim_data)
plot_transactions_over_time(sim_data)
plot_sender_distance_boxplot(sim_data)

# Plotting the heatmap
plt.figure(figsize=(10, 8))
plt.imshow(heatmap_data, cmap='hot', interpolation='nearest')

# Labeling
skewness_labels = [s.replace('_', '\n') for s in skewness_levels]
plt.xticks(ticks=range(len(skewness_levels)), labels=skewness_labels)
plt.yticks(ticks=range(len(shard_counts)), labels=shard_counts)
plt.xlabel('Skewness of Distribution')
plt.ylabel('Number of Shards')
plt.colorbar(label='Nonce Gap Frequency')
plt.title('Nonce Gap Frequency Heatmap')

# Add text annotations to each cell (as percentages)
for i in range(len(shard_counts)):
    for j in range(len(skewness_levels)):
        value = heatmap_data[i, j] * 100  # Convert to percentage
        plt.text(j, i, f'{value:.1f}%', ha='center', va='center', color='green', fontsize=8)

plt.savefig('nonce_gap_heatmap.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved: nonce_gap_heatmap.png")
