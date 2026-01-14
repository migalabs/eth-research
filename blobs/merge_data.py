#!/usr/bin/env python3
"""Merge blob data from two sources based on a slot cutoff point.

Uses data from source1 for all slots before the cutoff slot,
and data from source2 for the cutoff slot and all subsequent slots.
"""

import argparse
import csv
import os
import sys


def read_csv_rows(filepath):
    """Read all rows from a CSV file, returning header and rows."""
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    return header, rows


def get_slot_from_row(row, slot_index):
    """Extract slot number from a row."""
    return int(row[slot_index])


def merge_csv_files(file1, file2, output_file, cutoff_slot, slot_column='f_slot'):
    """Merge two CSV files based on slot cutoff.

    Takes rows with slot < cutoff_slot from file1,
    and rows with slot >= cutoff_slot from file2.
    """
    # Read both files
    header1, rows1 = read_csv_rows(file1)
    header2, rows2 = read_csv_rows(file2)

    # Verify headers match
    if header1 != header2:
        print(f"Warning: Headers differ between {file1} and {file2}", file=sys.stderr)
        print(f"  Source 1: {header1}", file=sys.stderr)
        print(f"  Source 2: {header2}", file=sys.stderr)

    # Find slot column index
    try:
        slot_index = header1.index(slot_column)
    except ValueError:
        print(f"Error: Column '{slot_column}' not found in {file1}", file=sys.stderr)
        sys.exit(1)

    # Filter rows from source 1 (slots < cutoff)
    rows_from_1 = [row for row in rows1 if get_slot_from_row(row, slot_index) < cutoff_slot]

    # Filter rows from source 2 (slots >= cutoff)
    rows_from_2 = [row for row in rows2 if get_slot_from_row(row, slot_index) >= cutoff_slot]

    # Combine and sort by slot
    merged_rows = rows_from_1 + rows_from_2
    merged_rows.sort(key=lambda row: get_slot_from_row(row, slot_index))

    # Write output
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header1)
        writer.writerows(merged_rows)

    return len(rows_from_1), len(rows_from_2), len(merged_rows)


def main():
    parser = argparse.ArgumentParser(
        description='Merge blob data from two sources based on a slot cutoff point.'
    )
    parser.add_argument('--source1', '-s1', type=str, required=True,
                        help='Path to first data source directory (used for slots < cutoff)')
    parser.add_argument('--source2', '-s2', type=str, required=True,
                        help='Path to second data source directory (used for slots >= cutoff)')
    parser.add_argument('--slot', '-s', type=int, required=True,
                        help='Cutoff slot: source1 for slots before this, source2 for this slot and after')
    parser.add_argument('--output', '-o', type=str, default='./merged',
                        help='Output directory for merged files (default: ./merged)')
    args = parser.parse_args()

    # Define the data files to merge
    data_files = ['BlobsPerSlot.csv', 'MissedSlots.csv']

    # Check source directories exist
    for source_name, source_path in [('source1', args.source1), ('source2', args.source2)]:
        if not os.path.isdir(source_path):
            print(f"Error: {source_name} directory not found: {source_path}", file=sys.stderr)
            sys.exit(1)

    # Check all required files exist in both sources
    missing_files = []
    for source_path in [args.source1, args.source2]:
        for filename in data_files:
            filepath = os.path.join(source_path, filename)
            if not os.path.isfile(filepath):
                missing_files.append(filepath)

    if missing_files:
        print("Error: Required data file(s) not found:", file=sys.stderr)
        for f in missing_files:
            print(f"  - {f}", file=sys.stderr)
        sys.exit(1)

    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)

    print(f"Merging data with cutoff at slot {args.slot}")
    print(f"  Source 1 (slots < {args.slot}): {args.source1}")
    print(f"  Source 2 (slots >= {args.slot}): {args.source2}")
    print(f"  Output: {args.output}")
    print()

    # Merge each data file
    for filename in data_files:
        file1 = os.path.join(args.source1, filename)
        file2 = os.path.join(args.source2, filename)
        output_file = os.path.join(args.output, filename)

        count1, count2, total = merge_csv_files(file1, file2, output_file, args.slot)

        print(f"{filename}:")
        print(f"  Rows from source1: {count1}")
        print(f"  Rows from source2: {count2}")
        print(f"  Total merged rows: {total}")
        print(f"  Written to: {output_file}")
        print()

    print("Merge complete.")


if __name__ == "__main__":
    main()
