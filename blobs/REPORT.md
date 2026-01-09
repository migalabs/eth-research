# Ethereum Blob Analysis: Fusaka Update and BPO Changes

## Overview

This report analyzes the impact of the Fusaka hard fork and subsequent Blob-Parameter-Only (BPO) changes on Ethereum's blob throughput and network stability.

### Key Dates

| Event | Date |
|-------|------|
| Data collection start | October 1, 2025 |
| **Fusaka hard fork** | December 3, 2025 |
| **BPO Change #1** | December 9, 2025 |
| **BPO Change #2** | January 7, 2026 |

## Analysis Period

- **Box plot analysis**: Last 50 days (November 20, 2025 - January 9, 2026)
- **Missed slots analysis**: Last 20 days (December 19, 2025 - January 8, 2026)

## Key Findings

### 1. Fusaka Transition Impact

The Fusaka hard fork on December 3rd caused a significant but temporary disruption:

- **Missed slots spike**: Approximately 420 missed slots on December 3rd, representing a ~6x increase from the baseline of ~60-80 missed slots per day
- **Rapid recovery**: Missed slots returned to normal levels (~20-40 per day) within 2-3 days after the upgrade
- **Blob capacity increase**: Post-Fusaka, the network began processing higher blob counts per slot

### 2. Blob Distribution Changes

**Pre-Fusaka (before Dec 3):**
- Blob counts per slot ranged from 0-9
- Median around 4-6 blobs per slot
- Very few outliers

**Post-Fusaka and BPO changes (Dec 19 - Jan 8):**
- Blob counts now range from 0-21 per slot
- Distribution shows:
  - ~29,000 slots with 0 blobs (highest frequency)
  - ~17,000 slots with 1 blob
  - ~17,000 slots with 5 blobs
  - Significant tail extending to 15+ blobs
- Outliers regularly reaching 15-21 blobs per slot

### 3. Missed Slots Analysis

During the 20-day post-BPO period (Dec 19 - Jan 8):

**Blob count in slots preceding missed slots:**
- Most missed slots (~128) occurred after slots with 0 blobs
- ~90 missed slots after slots with 1 blob
- ~77 missed slots after slots with 6 blobs
- Distribution roughly follows the overall blob distribution

**Miss rate by blob count:**
- Baseline miss rate: ~0.4-0.6% for blob counts 0-14
- Elevated miss rate at 15 blobs: ~0.85%
- Significantly elevated miss rate at 18 blobs: ~2.7%

This suggests that **very high blob counts (15+) may correlate with slightly increased miss rates**, though the sample size for these extreme values is small.

### 4. Network Stability Post-BPO

The data shows the network has stabilized well after the BPO changes:

- Missed slots per day have decreased from the Fusaka spike (~420) to a stable ~20-40 per day
- The network is successfully processing higher blob throughput
- No sustained increase in miss rates correlated with increased blob capacity

## Conclusions

1. **Fusaka transition was successful** despite initial disruption, with the network quickly adapting to new parameters

2. **Blob capacity has increased significantly** - the network now regularly processes 15+ blobs per slot compared to the pre-Fusaka maximum of ~9

3. **Network stability remains strong** - miss rates have returned to baseline levels and remain consistent across most blob counts

4. **Potential concern at extreme blob counts** - slots with 15+ blobs show elevated miss rates (0.85-2.7% vs 0.4-0.6% baseline), warranting continued monitoring

## Methodology

Data was collected from:
- `BlobsPerSlot.csv`: Records of blob indices per slot
- `MissedSlots.csv`: Records of proposed/missed slots

Analysis performed using `load_blobs.py` with parameters:
- `--days 50`: 50-day window for daily distribution analysis
- `--missed 20`: 20-day window for missed slot correlation analysis

---

*Report generated: January 9, 2026*
