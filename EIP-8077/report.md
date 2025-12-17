# EIP-8077: Nonce Gap Simulation Report

## Executive Summary

This report presents the results of a Monte Carlo simulation analyzing the frequency of **nonce gaps** in a sharded blob mempool environment. A nonce gap occurs when consecutive blob transactions (type-3) from the same sender are assigned to different shards within the same slot, potentially causing transaction ordering issues for block proposers.

**Key Finding:** With random shard assignment, a significant percentage of blob transactions (up to ~36% in worst-case scenarios) are affected by nonce gaps. The frequency depends on both the number of shards and the skewness of transaction distribution among senders. This highlights the need for improved transaction announcement mechanisms as proposed in EIP-8077.

---

## 1. Motivation: Supporting EIP-8077

### 1.1 Scope: Blob Transactions and Mempool Sharding

This analysis focuses exclusively on **type-3 transactions (blob transactions)** introduced in EIP-4844. We specifically examine the sharding of the **blob mempool** rather than the regular transaction mempool for the following reasons:

1. **Blob size**: Each blob is 128KB, significantly larger than regular transactions (typically < 1KB)
2. **Bandwidth consumption**: Blob propagation dominates network bandwidth usage
3. **Scalability pressure**: As L2 adoption grows, blob demand increases, making mempool sharding essential
4. **Concentrated senders**: Blob transactions come primarily from L2 sequencers (Base, Optimism, Arbitrum, etc.), creating highly skewed sender distributions

Sharding the blob mempool allows nodes to subscribe to a subset of blobs, reducing bandwidth requirements while maintaining network connectivity. However, this introduces the nonce gap problem that this study quantifies.

### 1.2 The Problem

[EIP-8077](https://eips.ethereum.org/EIPS/eip-8077) proposes extending Ethereum's devp2p protocol to include sender address and nonce information in transaction announcements. This simulation study provides quantitative evidence for why this enhancement is necessary.

In a sharded blob mempool, blob transactions from the same sender (e.g., an L2 sequencer) may be distributed across different shards or arrive at different times. When a block proposer receives blob transactions, they need to:

1. **Order transactions correctly** by nonce for each sender
2. **Identify nonce gaps** that would make transactions temporarily unincludable
3. **Prioritize fetching** transactions that fill gaps over those that create new ones

Without sender and nonce information in announcements, nodes must:
- Fetch transactions blindly, risking nonce gaps
- Use inefficient trial-and-error to fill gaps
- Maintain large transaction hash caches
- Miss opportunities for selective fetching by source address

### 1.2 Why This Study Matters

This simulation quantifies the **scale of the nonce gap problem** under realistic conditions:

- **Up to 36% of transactions** can be affected by nonce gaps in high-skewness, high-shard scenarios
- **Skewness significantly impacts gap frequency** - networks with dominant senders (major L2 sequencers like Base, Optimism, Arbitrum) face higher gap rates
- **Same-slot analysis** focuses on what matters to proposers - gaps within a single block building period

These findings demonstrate that as Ethereum scales (more shards, higher throughput), intelligent transaction fetching becomes critical. EIP-8077's metadata enables nodes to make informed decisions about which transactions to fetch, reducing wasted bandwidth and improving mempool consistency.

### 1.3 Key Implications for EIP-8077

| Finding | Implication for EIP-8077 |
|---------|-------------------------|
| Up to 36% gap rate | Significant portion of blob transactions affected without smart fetching |
| Skewness matters | High-volume L2 sequencers (Base, Optimism, Arbitrum) disproportionately impacted |
| Same-slot gaps are common | Proposers need real-time nonce information for efficient block building |
| More shards = more gaps | Problem worsens as blob mempool sharding increases |

---

## 2. Simulation Parameters

### 2.1 Configurable Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| NUM_SLOTS | 216,000 | 30 days worth of slots |
| AVG_TX_PER_SLOT | 14 | Target average transactions per slot |
| MAX_TX_PER_SLOT | 21 | Maximum transactions per slot (chain capacity) |
| NUM_SENDERS | 100 | Number of unique senders |

### 2.2 Derived Values

| Metric | Value |
|--------|-------|
| Simulation period | 30 days |
| Slots per hour | 300 |
| Max transactions per hour | 6,300 |
| Total transactions (approx.) | ~3 million |

### 2.3 Shard Configurations

Six shard configurations were tested:

| Configuration | Number of Shards |
|---------------|------------------|
| 1 | 1 (baseline) |
| 2 | 2 |
| 3 | 4 |
| 4 | 8 |
| 5 | 16 |
| 6 | 32 |

### 2.4 Skewness Configurations

Six sender distribution patterns were modeled using exponential decay functions `P(i) = exp(-λ * i)`:

| Skewness Level | Decay Rate (λ) | Description |
|----------------|----------------|-------------|
| Very High | 0.15 | Extreme concentration on few senders (e.g., major L2s like Base, Optimism) |
| High | 0.10 | Strong concentration (e.g., multiple active L2 sequencers) |
| Medium High | 0.07 | Moderate-high concentration |
| Medium Low | 0.04 | Moderate-low concentration |
| Low | 0.02 | Slight concentration |
| Uniform | 0.00 | Equal probability for all senders |

---

## 3. Methodology

### 3.1 Transaction Distribution Over Time

Transactions are distributed across the simulation period with **random, non-periodic patterns** to simulate realistic network activity:

1. **Random Base Noise**: Each slot starts with a random transaction rate centered around the target average
2. **Random Bursts**: 200 random activity bursts with varying duration (50-2000 slots) and intensity (1.2x-2.0x)
3. **Random Lulls**: 100 random low-activity periods with varying duration (100-1500 slots) and intensity (0.3x-0.7x)
4. **Capacity Cap**: All slots are capped at MAX_TX_PER_SLOT

![Transaction Rate Over Time](transactions_over_time.png)

*Figure 1: Transaction rate over the 30-day simulation period showing random bursts and lulls (no artificial periodicity).*

### 3.2 Sender Distribution

The probability of a transaction being sent by sender `i` follows an exponential distribution:

```
P(sender = i) = exp(-λ * i) / Σ exp(-λ * j)
```

Where `λ` is the decay rate controlling skewness.

![Transaction Distribution](transaction_distribution.png)

*Figure 2: Probability distribution showing how transaction frequency varies across senders for different skewness levels.*

![Transactions Per Sender](transactions_per_sender.png)

*Figure 3: Absolute number of transactions per sender for each distribution type.*

### 3.3 Same-Sender Transaction Distance

An important factor in nonce gap frequency is how often the same sender has multiple transactions within the same slot. This depends on the skewness of the distribution.

![Sender Distance Boxplot](sender_distance_boxplot.png)

*Figure 4: Distribution of slot distances between consecutive transactions from the same sender. More skewed distributions result in shorter distances (more same-slot pairs).*

### 3.4 Shard Assignment

Each transaction is assigned to a shard **uniformly at random**:

```python
shard = random.randint(0, num_shards - 1)
```

This models a scenario where shard assignment is independent of sender identity.

### 3.5 Nonce Gap Measurement

**Critical Design Decision**: We only count nonce gaps between consecutive same-sender transactions that occur **within the same slot**. This is because:

- Different slots are built by different proposers
- A proposer only cares about nonce gaps within their own block
- Cross-slot gaps are irrelevant for block building

The metric we measure is:

```
Nonce Gap Frequency = (Shard Switches in Same-Slot Pairs) / (Total Transactions)
```

This represents the **percentage of all transactions that are involved in a same-slot nonce gap**.

---

## 4. Results

### 4.1 Nonce Gap Frequency Heatmap

![Nonce Gap Heatmap](nonce_gap_heatmap.png)

*Figure 5: Heatmap showing nonce gap frequency (as percentage of total transactions) across all shard and skewness configurations.*

### 4.2 Numerical Results

| Shards | Very High | High | Medium High | Medium Low | Low | Uniform |
|--------|-----------|------|-------------|------------|-----|---------|
| 1 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 2 | 18.6% | 13.7% | 10.8% | 6.9% | 4.6% | 3.6% |
| 4 | 27.6% | 21.1% | 16.1% | 10.5% | 7.0% | 5.5% |
| 8 | 32.3% | 24.4% | 19.0% | 12.2% | 8.1% | 6.4% |
| 16 | 34.6% | 26.0% | 19.8% | 12.8% | 8.8% | 6.7% |
| 32 | 36.0% | 27.2% | 20.9% | 13.5% | 9.1% | 6.9% |

### 4.3 Key Patterns

1. **Vertical Pattern (More Shards)**: Increasing shards increases gap frequency, but with diminishing returns
2. **Horizontal Pattern (More Skewness)**: Higher skewness dramatically increases gap frequency
3. **Worst Case**: Very high skewness + 32 shards = ~36% of transactions affected
4. **Best Case**: Uniform distribution + 2 shards = ~3.6% of transactions affected

---

## 5. Analysis

### 5.1 Why Skewness Matters

Unlike our initial hypothesis, **skewness significantly affects nonce gap frequency**. This is because:

1. **Skewed distributions concentrate transactions** among fewer senders
2. **Concentrated senders have more same-slot consecutive pairs**
3. **More same-slot pairs = more opportunities for nonce gaps**

With uniform distribution, blob transactions are spread across 100 senders, making same-slot consecutive pairs from the same sender rare. With very high skewness (reflecting a network dominated by major L2 sequencers like Base), a few dominant senders produce many same-slot consecutive pairs, each with a (N-1)/N probability of being a gap.

### 5.2 Why This Supports EIP-8077

| Observation | EIP-8077 Benefit |
|-------------|------------------|
| High-volume L2 sequencers create more gaps | Nodes can prioritize fetching complete nonce sequences for major L2s |
| Same-slot gaps affect block building | Proposers need immediate nonce information to build valid blocks |
| Gap frequency varies by sender | Selective fetching by sender address becomes valuable |
| Up to 36% blob transactions affected | Significant efficiency gains possible with smart fetching |

### 5.3 Implications for Different Network Conditions

| Scenario | Gap Rate | EIP-8077 Value |
|----------|----------|----------------|
| L2-dominated (high skewness, many shards) | 27-36% | Critical - major L2 sequencers need priority handling |
| Mixed L2 ecosystem (high skewness, few shards) | 14-19% | High - multiple L2s need consistent ordering |
| Diverse blob senders (low skewness) | 4-9% | Moderate - still beneficial for efficiency |
| Single shard | 0% | Low - no sharding means no gaps |

---

## 6. Conclusions

### 6.1 Key Findings

1. **Nonce gaps are a significant problem**: Up to 36% of transactions can be affected in high-skewness, high-shard scenarios.

2. **Skewness is a major factor**: Networks with dominant blob senders (major L2 sequencers like Base, Optimism, Arbitrum) face substantially higher gap rates than networks with uniform transaction distribution.

3. **Sharding exacerbates the problem**: More shards = more gaps, following (N-1)/N probability for each same-slot pair.

4. **Same-slot analysis is critical**: Focusing on what matters to proposers (gaps within their block-building window) gives actionable insights.

### 6.2 Support for EIP-8077

This simulation provides strong quantitative support for EIP-8077:

- **The problem is real**: A significant percentage of transactions are affected by nonce gaps
- **The problem is scalable**: It worsens as Ethereum adds more shards/throughput
- **The solution is targeted**: Sender/nonce metadata enables intelligent fetching
- **The benefit is measurable**: Nodes can reduce wasted bandwidth and improve block building efficiency

### 6.3 Recommendations

1. **Adopt EIP-8077** to provide nodes with the metadata needed for intelligent blob transaction fetching
2. **Prioritize major L2 sequencers** when fetching to maintain complete nonce sequences for high-volume blob senders
3. **Consider sender-aware shard assignment** as a complementary strategy to reduce gaps at the protocol level

---

## 7. Future Work

- Simulate the impact of EIP-8077's metadata on fetching efficiency
- Model different fetching strategies enabled by sender/nonce information
- Analyze real Ethereum mainnet transaction patterns for skewness calibration
- Consider dynamic shard rebalancing scenarios
- Study the interaction with other scaling solutions (rollups, data availability sampling)

---

## Appendix: Code Structure

The simulation is implemented in `simu.py` with the following components:

| Function | Purpose |
|----------|---------|
| `get_sender_distribution()` | Generates probability distribution for sender selection |
| `generate_transaction_rate()` | Creates random, non-periodic transaction patterns |
| `simulate_nonce_gaps()` | Main simulation function (same-slot analysis) |
| `plot_distributions()` | Visualizes sender probability distributions |
| `plot_transactions_per_sender()` | Shows absolute transaction counts |
| `plot_transactions_over_time()` | Displays temporal burstiness (bar chart, per hour) |
| `plot_sender_distance_boxplot()` | Shows distribution of same-sender transaction distances |

**Configurable Parameters** (at top of `simu.py`):
```python
NUM_SLOTS = 216000        # 30 days worth of slots
AVG_TX_PER_SLOT = 14      # Target average transactions per slot
MAX_TX_PER_SLOT = 21      # Maximum transactions per slot
NUM_SENDERS = 100         # Number of unique senders
```

**Dependencies**: numpy, matplotlib, random

---
