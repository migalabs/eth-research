# Ethereum Blob Analysis: Fusaka Hard Fork and BPO Parameter Updates

## Executive Summary

This report presents an empirical analysis of Ethereum's blob throughput and network stability following the Fusaka hard fork and subsequent Blob-Parameter-Only (BPO) updates. The study examines blob distribution patterns, missed slot correlations, and overall network health across a multi-month observation period.

### Timeline of Events

| Event | Date | Description |
|-------|------|-------------|
| Data Collection Start | October 1, 2025 | Baseline measurement period begins |
| **Fusaka Hard Fork** | December 3, 2025 | Target blobs increased from 6 to 9 |
| **BPO Update #1** | December 9, 2025 | Target blobs increased from 9 to 12 |
| **BPO Update #2** | January 7, 2026 | Target blobs increased from 12 to 14 |

## Analysis

### Blob Distribution per Slot

The temporal evolution of blob counts per slot was recorded throughout the observation period, along with corresponding missed slot data. Figure 1 presents the daily distribution of blobs per slot as a boxplot, with missed slot counts overlaid on the secondary axis.

![Figure 1: Daily distribution of blobs per slot with missed slot overlay](blobs_per_day_boxplot.png)
*Figure 1: Boxplot showing the daily distribution of blobs per slot (left axis) and the number of missed slots per day (right axis). Vertical dashed lines indicate protocol upgrade events.*

The data reveals several noteworthy observations:

1. **No correlation between blob count and missed slots**: Despite the progressive increase in maximum blob capacity—from 9 (pre-Fusaka) to 15 (post-BPO1) to 21 (post-BPO2)—there is no discernible increase in daily missed slot frequency. This suggests that the network infrastructure has successfully accommodated the increased data throughput.

2. **Median blob count remains stable**: While maximum blob counts have increased substantially, the median number of blobs per slot has not exhibited corresponding growth. Post-BPO2, the network is not consistently reaching the target of 14 blobs per slot. This indicates that current demand for blob space may not fully utilize the expanded capacity, though demand patterns may evolve over time.

### Missed Slot Correlation Analysis

To investigate potential correlations between blob counts and subsequent missed slots, we analyzed the frequency of missed blocks following slots with varying blob counts.

![Figure 2: Missed blocks by preceding blob count](blobs_before_missed.png)
*Figure 2: Absolute count of missed blocks categorized by the number of blobs in the preceding slot.*

The raw data in Figure 2 suggests a higher incidence of missed blocks following slots with zero or few blobs. However, this observation requires normalization to account for the non-uniform distribution of blob counts across the network.

![Figure 3: Blob count distribution](blob_distribution.png)
*Figure 3: Distribution of blob counts across all observed slots, demonstrating the non-uniform frequency of different blob counts.*

To obtain an accurate assessment of miss probability, we computed the normalized miss rate using the following formula:

$$\text{Miss Rate}(x) = \frac{\text{Missed blocks after slots with } x \text{ blobs}}{\text{Total slots with } x \text{ blobs}} \times 100$$

![Figure 4: Normalized miss rate by blob count](miss_rate_by_blobs.png)
*Figure 4: Probability of a missed block following a slot with a given number of blobs.*

The normalized analysis reveals:

- **Baseline miss rate (0-14 blobs)**: Approximately 0.5% across all blob counts, demonstrating consistent network behavior within the original parameter range.
- **Elevated miss rate at 15 blobs**: Increases to approximately 0.85%, representing a 70% increase over baseline.
- **Significant elevation at 18 blobs**: Rises to approximately 2.7%, representing a five-fold increase over baseline rates.

### Statistical Considerations

The current dataset, particularly for high blob counts following BPO2, remains limited. The elevated miss rates observed at 15+ blobs should be interpreted as preliminary indicators rather than definitive conclusions. Extended observation periods are required to establish statistical significance and confirm these trends.

## Conclusions

1. **Successful Fusaka transition**: The network demonstrated rapid adaptation to the new parameters, with no sustained disruption to normal operations.

2. **Substantial capacity expansion**: The network now regularly processes 15+ blobs per slot, compared to the pre-Fusaka maximum of 9, representing a significant increase in data availability throughput.

3. **Maintained network stability**: Miss rates have stabilized at baseline levels and remain consistent across the majority of blob count ranges.

4. **Elevated miss rates at extreme blob counts**: Slots containing 15+ blobs exhibit miss rates of 0.85-2.7%, compared to the 0.4-0.6% baseline. This warrants continued monitoring before considering further capacity increases.

5. **Recommendation for cautious progression**: Prior to implementing additional BPO updates, the network should be observed operating at sustained high blob counts to validate that elevated miss rates do not compound under continuous load. Premature capacity increases risk L2 protocols adapting to new limits and potentially saturating network capacity.

## Methodology

### Data Sources

- `BlobsPerSlot.csv`: Per-slot blob index records
- `MissedSlots.csv`: Proposer duty and missed slot records

### Analysis Parameters

Analysis was performed using `load_blobs.py` with the following configuration:
- `--days 50`: 50-day rolling window for daily distribution analysis
- `--missed 20`: 20-day window for missed slot correlation analysis

---

*Report generated: January 9, 2026*
