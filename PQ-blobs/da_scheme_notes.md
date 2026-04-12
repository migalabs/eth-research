# Data Availability Scheme — Design Notes

## 1. Problem Statement

**Data Availability (DA)** is a core challenge in blockchain design: how can participants verify that the data needed to reconstruct the chain state (e.g. transaction blobs) was actually published by the block producer — without every node downloading everything?

The canonical attack is **block withholding**: a malicious block producer publishes a block header but suppresses one or more blobs. If no honest node downloaded the suppressed blob, it is permanently lost, making fraud undetectable and potentially allowing funds to be stolen.

### Why not just use Ethereum Danksharding?

Ethereum's Danksharding approach relies on two cryptographic primitives:

- **KZG polynomial commitments** — allow nodes to verify a chunk of data belongs to a polynomial that encodes the blob.
- **Erasure coding** — extends each blob so that any 50% of the chunks is sufficient to reconstruct the full blob.

These two together enable *Data Availability Sampling (DAS)*: light nodes randomly download small chunks; if the blob was withheld the samples will fail with high probability.

The scheme described here explores an **alternative** that requires neither erasure codes nor KZG commitments, relying instead on probabilistic redundancy through random node assignment.

---

## 2. Proposed Scheme: Random Blob Assignment

### Core idea

Each block contains **B blobs** of size **L KB**. Instead of sampling coded chunks, each node independently selects a subset of blobs to download in full:

- **Super nodes** download *all* B blobs every slot.
- **Full nodes** download *b* blobs chosen uniformly at random, using a deterministic seed `H(node_id ∥ block_hash)`.

Data availability is guaranteed as long as **every blob is held by at least one honest node**.

### Why no erasure codes or KZG?

- **Integrity** is provided by simple cryptographic hashes: the block header commits to the hash of each blob. Any downloaded blob is verified against it.
- **Routing** is provided by a DHT keyed on `(block_hash, blob_index)`, resolving to the set of nodes assigned to that blob. Any node can retrieve blob *i* in O(1) lookups (reachable within the network diameter).
- **Detection** of withholding: if an honest node fails to download a blob it is assigned to, it withholds its attestation and the block is rejected.

### Assignment privacy

The seed `H(node_id ∥ block_hash)` is only computable after the block hash is known (i.e. after the producer has committed). This prevents a malicious producer from computing which blobs have the fewest honest holders before deciding which to withhold.

---

## 3. Network Parameters

| Symbol | Meaning | Default |
|--------|---------|---------|
| N | Total nodes in the network | 10,000 |
| S | Fraction of nodes that are super nodes | swept: 2–8% |
| h | Fraction of nodes that are honest | swept: 1–4% |
| B | Number of blobs per block | swept: 32–256 |
| L | Size of each blob | 128 KB |
| T | Slot duration | 12 s |
| b | Blobs downloaded per full node (to find) | — |
| m | Maximum tolerated failure probability | 1×10⁻⁸ |

Derived quantities:

```
N_s = round(S × N)       # number of super nodes
N_f = N - N_s            # number of full nodes
```

---

## 4. Probabilistic Model

### Honesty model

Every node — super or full — is independently honest with probability **h**, and malicious with probability **1 − h**. Only honest nodes serve data.

This captures the worst-case scenario where the adversary controls a fixed fraction of the network but cannot choose *which* specific nodes to corrupt (corruption is treated as an independent random event per node).

> **Note on the strategic adversary**: if the adversary could choose optimally, they would corrupt all super nodes first (since each super node covers all B blobs). This would leave exactly `N × h` honest full nodes regardless of S, recovering the single-tier result. The probabilistic model is therefore the more interesting and realistic one for a decentralised network with unknown node identities.

### Per-blob failure probability

For a specific blob *i*:

**Super nodes miss blob *i*** only if every super node is malicious:

```
P(super nodes miss blob i) = (1 − h)^{N_s}
```

**Full nodes miss blob *i*** when no honest full node is assigned to it. A full node covers blob *i* with probability:

```
P(full node covers blob i) = h × (b / B)
```

because the node must be honest (probability h) *and* randomly assigned to blob *i* (probability b/B). The complementary probability per full node is `1 − h×b/B`, so:

```
P(full nodes miss blob i) = (1 − h × b/B)^{N_f}
```

Since super-node and full-node failures are **independent** (disjoint node sets):

```
P(blob i missing) = (1 − h)^{N_s}  ×  (1 − h × b/B)^{N_f}
```

### Overall failure probability (union bound)

Applying the union bound over all B blobs:

```
P(failure) ≤ B × (1 − h)^{N_s} × (1 − h × b/B)^{N_f}
```

This is an **upper bound**. It is tight when the per-blob failure probability is small (which it is in all practically relevant cases).

We require:

```
P(failure) < m
```

### Analytical lower bound on *b*

Rearranging the inequality to solve for *b*:

```
(1 − h × b/B)^{N_f}  <  A      where A = m / (B × (1 − h)^{N_s})
```

Taking logarithms (valid since 0 < A < 1):

```
N_f × ln(1 − h×b/B) < ln(A)

  ⟹  b  >  (B/h) × (1 − A^{1/N_f})
```

Special cases:
- If `B × (1 − h)^{N_s} ≤ m` (super nodes alone are sufficient): return b = 0.
- If A ≥ 1 or A ≤ 0: no solution exists; increase h, N, or S.

The calculator implements an exact integer search (brute-force over b = 0, 1, …, B) to find the minimum integer b satisfying the bound, using the analytical formula only as a cross-check.

---

## 5. Single-Tier Baseline (No Super Nodes)

With S = 0 (no super nodes), all N nodes are full nodes. The formula simplifies to:

```
P(failure) ≤ B × (1 − h × b/B)^N  <  m
```

For the reference network (N = 10,000, h = 1%, B = 64, m = 10⁻⁷):

| b | P(failure) |
|---|-----------|
| 7 | ~5.9×10⁻⁴ |
| 8 | ~1.0×10⁻⁴ |
| 9 | ~4.9×10⁻⁵ ✓ |

This was the starting point: **9 blobs per node** required to achieve P(failure) < 10⁻⁷ with 99% malicious nodes and no super nodes.

---

## 6. Two-Tier Result: Effect of Super Nodes

Introducing super nodes (S = 10%, N_s = 1,000) reduces the honest coverage needed from full nodes substantially. With h = 1%, m = 10⁻⁷:

| S | b required | Full-node download |
|---|---|---|
| 0% | 9 | 1,152 KB |
| 5% | 6 | 768 KB |
| 10% | 3 | 384 KB |

The super nodes contribute a factor of `(1 − h)^{N_s}` to the per-blob failure probability. With 1,000 super nodes at h = 1%: `(0.99)^{1000} ≈ 4.5×10⁻⁵`, which multiplies the full-node term and allows b to be much smaller.

---

## 7. Parameter Sweep and Heatmaps

The calculator sweeps all combinations of:

| Parameter | Values swept |
|-----------|-------------|
| `honest_fraction` h | 1%, 2%, 3%, 4% |
| `total_blobs` B | 32, 64, 128, 256 |
| `super_node_fraction` S | 2%, 4%, 6%, 8% |

For each combination it computes the minimum b and the achieved P(failure).

Four heatmap figures are produced (one per metric), each containing a 2×2 grid of subplots — one per S value (top row: S = 2% and 4%; bottom row: S = 6% and 8%). Within each subplot, rows are honest fractions (h) and columns are blob counts (B).

### Figure descriptions

| File | Metric | Colour interpretation |
|------|--------|----------------------|
| `da_heatmap_min_b.png` | Minimum blobs per full node (b) | Green = low b (cheap for nodes) |
| `da_heatmap_download_per_slot.png` | Data downloaded per slot (KB or MB) | Green = less download |
| `da_heatmap_bandwidth.png` | Bandwidth required (KB/s) | Green = low bandwidth |
| `da_heatmap_p_failure.png` | Achieved P(failure), log scale | Green = far below target (safer) |

All four figures use the **RdYlGn_r** colormap: red = high / bad, yellow = medium, green = low / good.

### Key observations from the heatmaps

1. **h dominates**: honest fraction is the most sensitive parameter. Moving from h = 1% to h = 4% drops the required b dramatically — often to 0 (super nodes alone suffice).

2. **Super nodes are a force multiplier**: even a small super node fraction (S = 2%) significantly reduces the full-node burden, because super nodes have an exponentially strong coverage guarantee.

3. **Blob count scales linearly**: doubling B roughly doubles the required download per node (b grows approximately proportionally to B for fixed h and S).

4. **Bandwidth is very manageable**: even in the worst case (h = 1%, B = 256, S = 2%), full nodes need ~620 KB/s — well within commodity hardware. Super nodes need at most ~2.7 MB/s for 256 blobs.

5. **The scheme degrades gracefully**: as h decreases toward 1%, the required b increases but remains bounded. The failure probability stays below the target even in extreme cases.

---

## 8. Derived Quantities

| Quantity | Formula |
|----------|---------|
| Full-node download per slot | `b × L` KB |
| Full-node bandwidth | `b × L / T` KB/s |
| Super-node download per slot | `B × L` KB |
| Super-node bandwidth | `B × L / T` KB/s |
| Expected honest copies of blob *i* (full nodes) | `h × N_f × b / B` |
| Expected honest copies of blob *i* (super nodes) | `h × N_s` |

---

## 9. Quantum Resistance

### Why this scheme is already quantum-resistant at the blob-integrity layer

Ethereum's original Danksharding design relies on **KZG polynomial commitments** to prove that a downloaded chunk belongs to a correctly erasure-coded blob. KZG opening proofs are based on elliptic curve pairings, which are broken by Shor's algorithm on a sufficiently powerful quantum computer.

This scheme eliminates that dependency entirely by design:

- Nodes download **complete blobs**, not coded chunks. There is no need for a chunk-membership proof.
- Blob integrity is verified by a plain hash comparison:

  ```
  SHA256(blob_data) == committed_hash_in_block_header
  ```

  The block header commits to a list (or Merkle root) of per-blob SHA-256 hashes. This is the only cryptographic primitive required for integrity.

### SHA-256 under quantum attack

| Property | Classical security | Quantum security | Algorithm |
|---|---|---|---|
| Preimage resistance | 256-bit | **128-bit** | Grover's algorithm (quadratic speedup) |
| Collision resistance | 128-bit | ~85-bit | BHT algorithm (requires large quantum memory) |

For **blob integrity**, preimage resistance is what matters: an adversary must not be able to produce a blob that hashes to the committed value. At 128-bit quantum security, SHA-256 remains strong.

Collision resistance (85-bit quantum bound) is relevant only if the block producer could find two different blobs with the same hash and later swap them. This is already outside the threat model (the producer commits the hash at block proposal time). If the bound is nonetheless a concern, replacing SHA-256 with **SHA-384** or **SHA3-256** restores a comfortable margin.

### What is *not* covered here

The quantum-resistance of the **consensus and attestation layer** (block producer signatures, validator attestations) is a separate concern. Those rely on ECDSA/EdDSA and *would* require replacement — e.g. with **CRYSTALS-Dilithium (ML-DSA, NIST FIPS 204)** — but that is outside the scope of the blob DA scheme itself.

### Summary

| Component | Quantum-resistant? | Notes |
|---|---|---|
| Blob integrity (SHA-256 hash) | ✓ Yes | 128-bit preimage security under Grover |
| KZG commitments | — Not applicable | Not used in this scheme |
| Erasure coding | — Not applicable | Not used in this scheme |
| Block/attestation signatures (ECDSA) | ✗ No | Out of scope for blob DA layer |

The blob data availability layer of this scheme requires **no modifications** to achieve quantum resistance.

---

## 10. FRI as a Quantum-Resistant Extension

### What is FRI?

**FRI** (Fast Reed-Solomon Interactive Oracle Proof of Proximity) is a cryptographic protocol that proves a committed function is close to a low-degree polynomial — i.e. that it lies within a Reed-Solomon codeword — without the verifier downloading the entire function. It is the core building block of **STARKs** (Scalable Transparent ARguments of Knowledge). Crucially, FRI relies exclusively on **hash functions and Merkle trees**, making it inherently quantum-resistant.

### What FRI replaces

In Ethereum's Danksharding design, KZG polynomial commitments serve two roles:
1. Encode the blob as a polynomial over a finite field.
2. Prove that a downloaded *chunk* belongs to the correct polynomial (a KZG opening proof).

FRI can replace both roles without elliptic curves or a trusted setup. The proof is constructed via a recursive folding procedure: given a function `f` evaluated at `N` points, the prover and verifier interact over `log N` rounds, each halving the domain using a random challenge `α`:

```
f'(x²) = (f(x) + f(-x)) / 2  +  α · (f(x) - f(-x)) / 2x
```

Each round is committed via a Merkle tree. The verifier spot-checks consistency at random positions. The entire proof uses only Merkle inclusion proofs — no pairings, no elliptic curves.

### FRI vs KZG

| Property | KZG | FRI |
|---|---|---|
| Cryptographic basis | Elliptic curve pairings | Hash functions only |
| Quantum resistant | No (Shor's algorithm) | Yes |
| Trusted setup | Required | Not required |
| Proof size | Constant (~48 bytes) | Logarithmic (~10–100 KB) |
| Verification time | O(1) | O(log N) |

### Relevance to this scheme

The current random-assignment scheme **does not need FRI** because nodes download complete blobs — no chunk-membership proof is required, and SHA-256 hashes suffice for integrity. However, FRI becomes relevant in two extension scenarios:

1. **Chunk-based sampling extension.** If the scheme is extended to allow nodes to download coded *chunks* instead of full blobs (to reduce per-node bandwidth further), FRI can replace KZG for the chunk-membership proof while preserving quantum resistance. This would re-introduce erasure coding but remove the elliptic-curve dependency.

2. **Hybrid fixed-plus-random assignment.** In the hybrid design (Section 8 of the assumptions), fixed-blob custodians could serve FRI-verified chunk proofs to other nodes on request, reducing `b_f` without sacrificing verifiability. This is a natural design point for a future extension.

3. **Complementary STARK-based DA schemes.** Projects such as Celestia and EigenDA use FRI-based commitments for their DA proofs. Understanding FRI positions this research to interoperate with or compare against those designs.

### Summary

FRI is the natural quantum-resistant upgrade path for the cryptographic component (KZG) that this scheme deliberately removes. It is not needed in the current design but is the correct tool to reach for if chunk-level proofs are reintroduced.

---

## 11. Assumptions and Limitations

- **Independent honesty**: the model assumes each node is honest independently with probability h. A coordinated adversary who knows node identities could concentrate corruption on super nodes, making the effective honest full-node count approach `N × h` regardless of S. The scheme should be designed so full nodes provide sufficient coverage even in this worst case.

- **Static assignment within a slot**: nodes are assigned blobs for the duration of one slot (12 s). Churn during the slot is not modelled. In practice, slightly higher b provides a safety buffer.

- **No network partition**: the model assumes any node can reach any other node (within the 7-hop diameter). Partitioning attacks are out of scope.

- **Union bound tightness**: the union bound overestimates P(failure) when per-blob failure probabilities are not negligible. For all parameter combinations of practical interest the individual probabilities are small enough that the bound is tight.

- **No Sybil resistance modelled**: the 1–4% honest fraction must be grounded in a staking or identity mechanism. Without Sybil resistance, an adversary can add nodes to dilute the honest fraction.

---

## 12. Relation to "Foundations of Data Availability Sampling" (Hall-Andersen, Simkin, Wagner — IACR CiC Vol. 1 Issue 4)

### Background: Examples 5 and 6 from the paper

The paper provides the first formal cryptographic treatment of DAS. Two key examples (Section 6.2) analyse the cost for **light clients** to collectively verify that a single block's codeword of N symbols is available, where each client issues Q random chunk queries.

**Example 5 — No erasure code (K = N, Δ = K − 1):**

Every symbol must be covered by at least one client query, so the adversary only needs to withhold a single symbol to break soundness.  Using the paper's Lemma 3 (sampling with replacement), the advantage against soundness is bounded by:

```
C(N, N−1) × (1 − 1/N)^{NQℓ} ≈ 2^{log N − Qℓ}
```

This is negligible only once:

```
Qℓ ≥ Ω(Nλ + N log N)
```

For N = 10,000 and λ = 128, this demands roughly **millions of total client queries per block** — completely impractical.

**Example 6 — Erasure code, rate 1/2 (N = 2K, Δ = K − 1 < N/2):**

Any K out of 2K symbols suffice to reconstruct.  The bound becomes:

```
2^{−Qℓ(1 − log_{1/2}(e))(K−1)} ≤ 2^{−Qℓ + 3K}
```

Negligible once:

```
Qℓ ≥ Ω(K + λ)
```

The total sample count now scales with **data size K**, not network size N — the entire motivation for erasure coding in DAS.

---

### Five Ways Our Scheme Differs

#### 1. Unit of operation

| | Paper framework | Our scheme |
|---|---|---|
| Unit | Individual symbols/chunks within one codeword | Complete blobs (128 KB each) |
| What is queried | A single field element | An entire blob |
| What needs coverage | T out of N chunk positions collectively | ≥ 1 honest node per blob independently |

The paper measures cost at chunk granularity.  Our scheme never samples chunks — nodes download whole blobs.

#### 2. Who pays the availability cost

- **Paper**: light clients issue Q queries each; ℓ clients collectively drive the soundness guarantee.
- **Our scheme**: full nodes download complete blobs assigned deterministically by `H(node_id ∥ block_hash)`.  There is no light-client sampling loop.  The cost is shifted from client query count to full-node download bandwidth (budgeted at ≤ 620 KB/s in the worst-case sweep).

#### 3. Why Example 5's blowup does not apply

Example 5's `Qℓ = Ω(Nλ + N log N)` blowup arises because light clients must collectively touch all N positions via tiny random probes.  Our scheme escapes this entirely:

- Full nodes download **complete** blobs — no partial queries.
- Availability is defined per-blob (`≥ 1 honest holder`), not "cover all N positions".
- With N = 10,000, h = 1%, b blobs per node: expected honest holders per blob ≈ `h × N_f × b / B` — a small, directly controllable quantity.

#### 4. Adversarial model

| | Paper | Our scheme |
|---|---|---|
| Adversary controls | The encoding π (can withhold any subset of symbols) | Which nodes are malicious (independently, prob. 1 − h) |
| Attack vector | Strategic symbol withholding | Block withholding only if every assigned honest node for a blob is also malicious |
| Assignment privacy | Not modelled | Seed `H(node_id ∥ block_hash)` — computable only after block commitment, preventing strategic targeting |

#### 5. Reconstruction model

- **Paper Example 5**: T = N distinct positions must be covered → full reconstruction requires all symbols → impractical without erasure codes.
- **Paper Example 6**: T = K distinct positions suffice → rate-1/2 erasure code makes this manageable.
- **Our scheme**: each blob is a self-contained unit verified by `SHA256(blob) == committed_hash_in_header`.  No reconstruction from partial data is needed.  Each blob is independently "available or not."

---

### The Core Tension and Design Space

The paper proves that without erasure codes, light-client DAS requires an impractically large number of queries (Example 5).  This is correct within the paper's model.

Our scheme sidesteps this by **changing the paradigm**: full nodes download whole blobs rather than light clients sampling chunks.  The two designs occupy different points in the cost-distribution space:

| Design axis | Paper framework (Examples 5/6) | Our scheme |
|---|---|---|
| Erasure coding needed? | Yes — Example 6 shows why for light-client DAS | No — blobs are atomic, independently hash-verified |
| Who pays the availability cost? | Light clients (many chunk queries) | Full nodes (complete blob downloads) |
| Quantum safety of commitment | KZG → broken by Shor; Hash construction → safe | SHA-256 → 128-bit preimage security under Grover |
| Closest paper construction | Hash-based (Section 9.1) for no-trusted-setup variant | Closer to a naive/Merkle baseline, but with probabilistic redundancy via random assignment rather than deterministic replication |

### Open Formal Question

The paper's soundness definition requires an extractor `Ext` that reconstructs data from enough client transcripts.  In our scheme, "retrieval" means fetching a complete blob from any honest holder over the DHT — a network-layer operation that the paper's model does not capture.  Mapping our scheme's guarantee ("each blob has ≥ 1 honest DHT holder") onto the paper's formal soundness definition (`Ext` succeeds from transcripts) remains an open formalisation task.
