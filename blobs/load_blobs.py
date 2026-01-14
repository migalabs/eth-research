import csv
import os
import sys
from collections import Counter
from datetime import datetime, timedelta

import matplotlib.pyplot as plt

# Constants
SLOTS_PER_DAY = 7200

# Key event slots
EVENT_SLOTS = {
    13164544: "Fusaka",
    13205504: "BPO #1",
    13410304: "BPO #2",
}
SLOT_DURATION_SECONDS = 12
REFERENCE_SLOT = 12704400  # First slot of October 1st, 2025 at 00:00:00 UTC
REFERENCE_DATE = datetime(2025, 10, 1, 0, 0, 0)


def slot_to_datetime(slot):
    """Convert a slot number to its corresponding datetime."""
    slot_diff = slot - REFERENCE_SLOT
    return REFERENCE_DATE + timedelta(seconds=slot_diff * SLOT_DURATION_SECONDS)


def load_blobs_per_slot(filepath):
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


def load_missed_slots(slots, filepath):
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
    if num_days is not None:
        min_slot = slot_ids[-1] - (num_days * SLOTS_PER_DAY)
        filtered_ids = [s for s in slot_ids if s >= min_slot]
    else:
        filtered_ids = slot_ids

    date_start = slot_to_datetime(filtered_ids[0])
    date_end = slot_to_datetime(filtered_ids[-1])

    return filtered_ids, date_start, date_end


def group_by_day(slots, slot_ids):
    """Group slots into daily batches by calendar date (UTC) and return blob counts and missed counts per day."""
    if not slots:
        return {}, {}

    days = {}
    missed_per_day = {}

    for slot_id in slot_ids:
        data = slots[slot_id]
        # Get actual calendar date for this slot
        slot_datetime = slot_to_datetime(slot_id)
        date_key = slot_datetime.date()
        if date_key not in days:
            days[date_key] = []
            missed_per_day[date_key] = 0
        days[date_key].append(data['count'])
        if data['missed']:
            missed_per_day[date_key] += 1

    return days, missed_per_day


def plot_blobs_per_day(days, missed_per_day, slot_ids, results_dir, num_days=None):
    """Create a box plot of blobs per day with missed slots on secondary axis.
    Returns the first and last slot used for this figure."""
    all_dates = sorted(days.keys())

    if num_days is not None and num_days < len(all_dates):
        dates = all_dates[-num_days:]
    else:
        dates = all_dates

    # Find first and last slots for the date range used
    first_date = dates[0]
    last_date = dates[-1]
    first_slot = None
    last_slot = None
    for slot_id in slot_ids:
        slot_date = slot_to_datetime(slot_id).date()
        if slot_date == first_date and first_slot is None:
            first_slot = slot_id
        if slot_date == last_date:
            last_slot = slot_id

    data = [days[d] for d in dates]
    missed_counts = [missed_per_day[d] for d in dates]

    # Use integer positions for plotting
    positions = list(range(len(dates)))

    fig, ax1 = plt.subplots(figsize=(14, 6))

    ax1.boxplot(data, positions=positions)
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Blobs per slot', color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')
    ax1.grid(axis='y', linestyle='--', alpha=0.7)

    ax2 = ax1.twinx()
    ax2.plot(positions, missed_counts, 'r-', linewidth=2, label='Missed slots')
    ax2.set_ylabel('Missed slots per day', color='red')
    ax2.tick_params(axis='y', labelcolor='red')

    # Add vertical lines for key events
    colors = ['green', 'purple', 'orange']
    for i, (event_slot, event_name) in enumerate(EVENT_SLOTS.items()):
        event_date = slot_to_datetime(event_slot).date()
        if event_date in dates:
            pos = dates.index(event_date)
            ax1.axvline(x=pos, color=colors[i % len(colors)], linestyle='--',
                       linewidth=2, alpha=0.8, label=event_name)

    # Add legend for event lines
    ax1.legend(loc='upper left')

    # Place ticks at regular intervals
    tick_interval = max(1, len(dates) // 6)  # Aim for ~6 ticks
    tick_indices = list(range(0, len(dates), tick_interval))
    tick_labels = [dates[i].strftime('%b %d') for i in tick_indices]
    ax1.set_xticks(tick_indices)
    ax1.set_xticklabels(tick_labels, rotation=45)

    ax1.set_title('Distribution of Blobs per Slot by Day')
    plt.tight_layout()
    output_path = os.path.join(results_dir, 'blobs_per_day_boxplot.png')
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"Saved plot to {output_path}")

    return first_slot, last_slot


def plot_blobs_before_missed(slots, slot_ids, date_start, date_end, results_dir):
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
    output_path = os.path.join(results_dir, 'blobs_before_missed.png')
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"Saved plot to {output_path}")


def plot_blob_distribution(slots, slot_ids, date_start, date_end, results_dir):
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
    output_path = os.path.join(results_dir, 'blob_distribution.png')
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"Saved plot to {output_path}")


def plot_miss_rate_by_blobs(slots, slot_ids, date_start, date_end, results_dir):
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
    output_path = os.path.join(results_dir, 'miss_rate_by_blobs.png')
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"Saved plot to {output_path}")


def write_random_slots(slots, slot_ids, results_dir, num_samples=100):
    """Write random slots to a CSV file for verification."""
    import random

    sample_size = min(num_samples, len(slot_ids))
    random_slot_ids = random.sample(slot_ids, sample_size)

    output_path = os.path.join(results_dir, 'random_slots.csv')
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['slot_id', 'count', 'missed'])
        for slot_id in sorted(random_slot_ids):
            data = slots[slot_id]
            writer.writerow([slot_id, data['count'], data['missed']])

    print(f"Saved {sample_size} random slots to {output_path}")


def write_high_blob_slots(slots, slot_ids, results_dir, min_blobs=16, figure_ranges=None):
    """Write slots with min_blobs or more blobs and their consecutive slot to a CSV file."""
    high_blob_entries = []

    for i, slot_id in enumerate(slot_ids):
        if slots[slot_id]['count'] >= min_blobs:
            # Get current slot data
            current_data = slots[slot_id]
            entry = {
                'slot_id': slot_id,
                'blob_count': current_data['count'],
                'missed': current_data['missed'],
                'next_slot_id': None,
                'next_blob_count': None,
                'next_missed': None,
            }
            # Get consecutive slot data if available
            next_slot_id = slot_id + 1
            if next_slot_id in slots:
                next_data = slots[next_slot_id]
                entry['next_slot_id'] = next_slot_id
                entry['next_blob_count'] = next_data['count']
                entry['next_missed'] = next_data['missed']

            high_blob_entries.append(entry)

    csv_path = os.path.join(results_dir, 'high_blob_slots.csv')
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['slot_id', 'blob_count', 'missed', 'next_slot_id', 'next_blob_count', 'next_missed'])
        for entry in high_blob_entries:
            writer.writerow([
                entry['slot_id'],
                entry['blob_count'],
                entry['missed'],
                entry['next_slot_id'],
                entry['next_blob_count'],
                entry['next_missed'],
            ])

    # Group by blob count for statistics (using ALL slots, not just high blob ones)
    stats_by_count = {}
    for slot_id in slot_ids:
        blob_count = slots[slot_id]['count']
        if blob_count not in stats_by_count:
            stats_by_count[blob_count] = {'total': 0, 'missed': 0}
        stats_by_count[blob_count]['total'] += 1
        # Check if next slot is missed
        next_slot_id = slot_id + 1
        if next_slot_id in slots and slots[next_slot_id]['missed']:
            stats_by_count[blob_count]['missed'] += 1

    print(f"Saved {len(high_blob_entries)} slots with {min_blobs}+ blobs to {csv_path}")

    # Write missed slot by blob count to markdown file
    md_filepath = os.path.join(results_dir, 'missedSlotByBlobCount.md')
    with open(md_filepath, 'w') as f:
        f.write("# Blob Analysis Report\n\n")

        # Write figure slot ranges if provided
        if figure_ranges:
            f.write("## Data Ranges Used per Figure\n\n")
            f.write("| Figure | First Slot | Last Slot | First Date | Last Date |\n")
            f.write("|--------|------------|-----------|------------|----------|\n")
            for figure_name, (first_slot, last_slot) in figure_ranges.items():
                first_date = slot_to_datetime(first_slot).strftime('%Y-%m-%d %H:%M:%S')
                last_date = slot_to_datetime(last_slot).strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"| {figure_name} | {first_slot} | {last_slot} | {first_date} | {last_date} |\n")
            f.write("\n")

        f.write("## Consecutive Missed Slots by Blob Count\n\n")
        f.write("| Blob Count | Total Slots | Missed Slots | Miss Rate (%) |\n")
        f.write("|------------|-------------|--------------|---------------|\n")
        for count in sorted(stats_by_count.keys()):
            total = stats_by_count[count]['total']
            missed = stats_by_count[count]['missed']
            ratio = (missed / total * 100) if total > 0 else 0
            f.write(f"| {count} | {total} | {missed} | {ratio:.2f} |\n")
    print(f"Saved missed slot statistics to {md_filepath}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Analyze blob data per slot')
    parser.add_argument('--data-dir', type=str, default='./data',
                        help='Path to directory containing data files (default: ./data)')
    parser.add_argument('--results-dir', type=str, default='./results',
                        help='Path to directory for output files (default: ./results)')
    parser.add_argument('--days', '-d', type=int, default=None,
                        help='Number of days for box plot (default: all days)')
    parser.add_argument('--missed', '-m', type=int, default=None,
                        help='Number of days for missed slots analysis (default: all days)')
    parser.add_argument('--random', '-r', type=int, default=100,
                        help='Number of random slots to export for verification (default: 100)')
    parser.add_argument('--high-blobs', '-b', type=int, default=16,
                        help='Minimum blob count for high blob slots export (default: 16)')
    args = parser.parse_args()

    # Create results directory if it doesn't exist
    os.makedirs(args.results_dir, exist_ok=True)

    # Build file paths from data directory
    blobs_file = os.path.join(args.data_dir, 'BlobsPerSlot.csv')
    missed_file = os.path.join(args.data_dir, 'MissedSlots.csv')

    # Check if data files exist
    missing_files = []
    if not os.path.isfile(blobs_file):
        missing_files.append(blobs_file)
    if not os.path.isfile(missed_file):
        missing_files.append(missed_file)

    if missing_files:
        print(f"Error: Required data file(s) not found:", file=sys.stderr)
        for f in missing_files:
            print(f"  - {f}", file=sys.stderr)
        sys.exit(1)

    # Load data
    slots = load_blobs_per_slot(blobs_file)
    slots = load_missed_slots(slots, missed_file)
    slot_ids = list(slots.keys())  # Already sorted from load_missed_slots

    print(f"Total unique slots: {len(slots)}")

    # Calculate total days in data and actual date range
    total_days = (slot_ids[-1] - slot_ids[0]) // SLOTS_PER_DAY + 1
    data_start = slot_to_datetime(slot_ids[0])
    data_end = slot_to_datetime(slot_ids[-1])
    print(f"Data range: {data_start.strftime('%Y-%m-%d %H:%M:%S')} to {data_end.strftime('%Y-%m-%d %H:%M:%S')}")
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
    boxplot_first, boxplot_last = plot_blobs_per_day(days, missed_per_day, slot_ids, args.results_dir, num_days=args.days)

    # Filter slots for missed analysis plots
    filtered_slot_ids, date_start, date_end = filter_slots_by_days(slot_ids, args.missed)

    # Generate remaining plots with pre-filtered data
    plot_blobs_before_missed(slots, filtered_slot_ids, date_start, date_end, args.results_dir)
    plot_blob_distribution(slots, filtered_slot_ids, date_start, date_end, args.results_dir)
    plot_miss_rate_by_blobs(slots, filtered_slot_ids, date_start, date_end, args.results_dir)

    # Build figure ranges dictionary
    figure_ranges = {
        'blobs_per_day_boxplot.png': (boxplot_first, boxplot_last),
        'blobs_before_missed.png': (filtered_slot_ids[0], filtered_slot_ids[-1]),
        'blob_distribution.png': (filtered_slot_ids[0], filtered_slot_ids[-1]),
        'miss_rate_by_blobs.png': (filtered_slot_ids[0], filtered_slot_ids[-1]),
    }

    # Export random slots for verification
    write_random_slots(slots, slot_ids, args.results_dir, num_samples=args.random)

    # Export high blob slots with their consecutive slots
    write_high_blob_slots(slots, slot_ids, args.results_dir, min_blobs=args.high_blobs, figure_ranges=figure_ranges)
