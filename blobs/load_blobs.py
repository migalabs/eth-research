import csv
from collections import Counter
from datetime import datetime, timedelta

import matplotlib.pyplot as plt

# Constants
SLOTS_PER_DAY = 7200
START_DATE = datetime(2025, 10, 1)


def load_blobs_per_slot(filepath="data/BlobsPerSlot.csv"):
    """Load blob data and count occurrences per slot."""
    slots = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            slot_id = int(row['f_slot'])
            if slot_id not in slots:
                slots[slot_id] = {'count': 0, 'missed': False}
            slots[slot_id]['count'] += 1
    return slots


def load_missed_slots(slots, filepath="data/MissedSlots.csv"):
    """Load missed slots and update the slots structure."""
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            slot_id = int(row['f_slot'])
            missed = row['f_proposed'].lower() != 'true'
            if slot_id not in slots:
                slots[slot_id] = {'count': 0, 'missed': missed}
            else:
                slots[slot_id]['missed'] = missed
    return dict(sorted(slots.items()))


def filter_slots_by_days(slot_ids, num_days):
    """Filter slot_ids to last num_days. Returns filtered list and date range."""
    first_slot = slot_ids[0]

    if num_days is not None:
        min_slot = slot_ids[-1] - (num_days * SLOTS_PER_DAY)
        filtered_ids = [s for s in slot_ids if s >= min_slot]
    else:
        filtered_ids = slot_ids

    first_day_num = (filtered_ids[0] - first_slot) // SLOTS_PER_DAY
    last_day_num = (filtered_ids[-1] - first_slot) // SLOTS_PER_DAY
    date_start = START_DATE + timedelta(days=first_day_num)
    date_end = START_DATE + timedelta(days=last_day_num)

    return filtered_ids, date_start, date_end


def group_by_day(slots, slot_ids):
    """Group slots into daily batches and return blob counts and missed counts per day."""
    if not slots:
        return {}, {}

    first_slot = slot_ids[0]
    days = {}
    missed_per_day = {}

    for slot_id in slot_ids:
        data = slots[slot_id]
        day_num = (slot_id - first_slot) // SLOTS_PER_DAY
        if day_num not in days:
            days[day_num] = []
            missed_per_day[day_num] = 0
        days[day_num].append(data['count'])
        if data['missed']:
            missed_per_day[day_num] += 1

    return days, missed_per_day


def plot_blobs_per_day(days, missed_per_day, num_days=None):
    """Create a box plot of blobs per day with missed slots on secondary axis."""
    all_day_numbers = sorted(days.keys())

    if num_days is not None and num_days < len(all_day_numbers):
        day_numbers = all_day_numbers[-num_days:]
    else:
        day_numbers = all_day_numbers

    data = [days[d] for d in day_numbers]
    missed_counts = [missed_per_day[d] for d in day_numbers]

    fig, ax1 = plt.subplots(figsize=(14, 6))

    ax1.boxplot(data, positions=day_numbers)
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Blobs per slot', color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')
    ax1.grid(axis='y', linestyle='--', alpha=0.7)

    ax2 = ax1.twinx()
    ax2.plot(day_numbers, missed_counts, 'r-', linewidth=2, label='Missed slots')
    ax2.set_ylabel('Missed slots per day', color='red')
    ax2.tick_params(axis='y', labelcolor='red')

    week_ticks = [d for d in day_numbers if d % 7 == 0]
    week_labels = [(START_DATE + timedelta(days=d)).strftime('%b %d') for d in week_ticks]
    ax1.set_xticks(week_ticks)
    ax1.set_xticklabels(week_labels, rotation=45)

    ax1.set_title('Distribution of Blobs per Slot by Day')
    plt.tight_layout()
    plt.savefig('blobs_per_day_boxplot.png', dpi=150)
    plt.close()
    print("Saved plot to blobs_per_day_boxplot.png")


def plot_blobs_before_missed(slots, slot_ids, date_start, date_end):
    """Create a bar plot of blob counts in slots just before missed slots."""
    blobs_before_missed = []
    for slot_id in slot_ids:
        if slots[slot_id]['missed']:
            prev_slot = slot_id - 1
            if prev_slot in slots:
                blobs_before_missed.append(slots[prev_slot]['count'])

    if not blobs_before_missed:
        print("No missed slots found in the selected period")
        return

    blob_counts = Counter(blobs_before_missed)
    x_values = sorted(blob_counts.keys())
    y_values = [blob_counts[x] for x in x_values]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x_values, y_values, color='steelblue', edgecolor='black')
    ax.set_xlabel('Number of blobs in slot before missed')
    ax.set_ylabel('Frequency')
    ax.set_title(f'Blob Count in Slots Preceding Missed Slots\n({date_start.strftime("%b %d, %Y")} - {date_end.strftime("%b %d, %Y")})')
    ax.set_xticks(x_values)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('blobs_before_missed.png', dpi=150)
    plt.close()
    print("Saved plot to blobs_before_missed.png")


def plot_blob_distribution(slots, slot_ids, date_start, date_end):
    """Create a bar plot showing distribution of blob counts across all slots."""
    blob_counts = [slots[s]['count'] for s in slot_ids]
    count_distribution = Counter(blob_counts)
    x_values = sorted(count_distribution.keys())
    y_values = [count_distribution[x] for x in x_values]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x_values, y_values, color='green', edgecolor='black')
    ax.set_xlabel('Number of blobs per slot')
    ax.set_ylabel('Number of slots')
    ax.set_title(f'Distribution of Blobs per Slot\n({date_start.strftime("%b %d, %Y")} - {date_end.strftime("%b %d, %Y")})')
    ax.set_xticks(x_values)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('blob_distribution.png', dpi=150)
    plt.close()
    print("Saved plot to blob_distribution.png")


def plot_miss_rate_by_blobs(slots, slot_ids, date_start, date_end):
    """Create a bar plot showing miss rate percentage after X blobs."""
    total_with_x = Counter()
    missed_after_x = Counter()

    for i, slot_id in enumerate(slot_ids[:-1]):
        blob_count = slots[slot_id]['count']
        total_with_x[blob_count] += 1
        next_slot = slot_ids[i + 1]
        if slots[next_slot]['missed']:
            missed_after_x[blob_count] += 1

    x_values = sorted(total_with_x.keys())
    percentages = [(missed_after_x[x] / total_with_x[x]) * 100 if total_with_x[x] > 0 else 0 for x in x_values]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x_values, percentages, color='orange', edgecolor='black')
    ax.set_xlabel('Number of blobs in slot')
    ax.set_ylabel('Miss rate (%)')
    ax.set_title(f'Miss Rate After Slots with X Blobs\n({date_start.strftime("%b %d, %Y")} - {date_end.strftime("%b %d, %Y")})')
    ax.set_xticks(x_values)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('miss_rate_by_blobs.png', dpi=150)
    plt.close()
    print("Saved plot to miss_rate_by_blobs.png")


def write_random_slots(slots, slot_ids, num_samples=100, filepath="random_slots.csv"):
    """Write random slots to a CSV file for verification."""
    import random

    sample_size = min(num_samples, len(slot_ids))
    random_slot_ids = random.sample(slot_ids, sample_size)

    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['slot_id', 'count', 'missed'])
        for slot_id in sorted(random_slot_ids):
            data = slots[slot_id]
            writer.writerow([slot_id, data['count'], data['missed']])

    print(f"Saved {sample_size} random slots to {filepath}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Analyze blob data per slot')
    parser.add_argument('--days', '-d', type=int, default=None,
                        help='Number of days for box plot (default: all days)')
    parser.add_argument('--missed', '-m', type=int, default=None,
                        help='Number of days for missed slots analysis (default: all days)')
    parser.add_argument('--random', '-r', type=int, default=100,
                        help='Number of random slots to export for verification (default: 100)')
    args = parser.parse_args()

    # Load data
    slots = load_blobs_per_slot()
    slots = load_missed_slots(slots)
    slot_ids = list(slots.keys())  # Already sorted from load_missed_slots

    print(f"Total unique slots: {len(slots)}")

    # Calculate total days in data
    total_days = (slot_ids[-1] - slot_ids[0]) // SLOTS_PER_DAY + 1
    print(f"Total days in data: {total_days}")

    # Validate parameters
    if args.days is not None and args.days > total_days:
        print(f"Warning: --days ({args.days}) exceeds available data ({total_days} days). Using all data.")
        args.days = None
    if args.missed is not None and args.missed > total_days:
        print(f"Warning: --missed ({args.missed}) exceeds available data ({total_days} days). Using all data.")
        args.missed = None

    # Group by day and plot box plot
    days, missed_per_day = group_by_day(slots, slot_ids)
    plot_blobs_per_day(days, missed_per_day, num_days=args.days)

    # Filter slots for missed analysis plots
    filtered_slot_ids, date_start, date_end = filter_slots_by_days(slot_ids, args.missed)

    # Generate remaining plots with pre-filtered data
    plot_blobs_before_missed(slots, filtered_slot_ids, date_start, date_end)
    plot_blob_distribution(slots, filtered_slot_ids, date_start, date_end)
    plot_miss_rate_by_blobs(slots, filtered_slot_ids, date_start, date_end)

    # Export random slots for verification
    write_random_slots(slots, slot_ids, num_samples=args.random)
