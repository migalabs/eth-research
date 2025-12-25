import hashlib
from dataclasses import dataclass
from typing import List, Optional, Tuple

def _hex_to_bytes(x: str) -> bytes:
    return bytes.fromhex(x.removeprefix("0x"))

def _uint64_to_bytes_le(x: int) -> bytes:
    # consensus-specs `uint_to_bytes(uint64(...))` is little-endian SSZ encoding
    return int(x).to_bytes(8, "little", signed=False)

def _sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()

def _xor_bytes(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))

def compute_base_fork_digest(fork_version_hex: str, genesis_validators_root_hex: str) -> str:
    """
    Base fork digest (Phase0..Electra style):
      digest = sha256( chunk0 || chunk1 )[:4]
    where:
      chunk0 = fork_version (Bytes4) right-padded with zeros to 32 bytes
      chunk1 = genesis_validators_root (Bytes32)
    """
    fv = _hex_to_bytes(fork_version_hex)
    gvr = _hex_to_bytes(genesis_validators_root_hex)

    if len(fv) != 4:
        raise ValueError("fork_version must be exactly 4 bytes (8 hex chars).")
    if len(gvr) != 32:
        raise ValueError("genesis_validators_root must be exactly 32 bytes (64 hex chars).")

    chunk0 = fv + b"\x00" * 28
    chunk1 = gvr
    root = _sha256(chunk0 + chunk1)
    return "0x" + root[:4].hex()

def compute_fork_digest_with_bpo_mask(
    fork_version_hex: str,
    genesis_validators_root_hex: str,
    blob_params: Optional[Tuple[int, int]] = None,  # (blob_params_epoch, max_blobs_per_block)
) -> str:
    """
    Fulu+ (EIP-7892) style:
      base_digest = compute_fork_data_root(fork_version, genesis_root)
      if blob_params provided:
        mask = sha256( uint64_le(blob_epoch) || uint64_le(max_blobs) )
        digest = (base_digest XOR mask)[:4]
      else:
        digest = base_digest[:4]

    This mirrors the Fulu spec’s modified compute_fork_digest. :contentReference[oaicite:2]{index=2}
    """
    # base_digest here is the 32-byte ForkData root (not just 4 bytes)
    fv = _hex_to_bytes(fork_version_hex)
    gvr = _hex_to_bytes(genesis_validators_root_hex)

    if len(fv) != 4:
        raise ValueError("fork_version must be exactly 4 bytes (8 hex chars).")
    if len(gvr) != 32:
        raise ValueError("genesis_validators_root must be exactly 32 bytes (64 hex chars).")

    chunk0 = fv + b"\x00" * 28
    base_digest_32 = _sha256(chunk0 + gvr)

    if blob_params is None:
        return "0x" + base_digest_32[:4].hex()

    blob_epoch, max_blobs = blob_params
    mask = _sha256(_uint64_to_bytes_le(blob_epoch) + _uint64_to_bytes_le(max_blobs))
    masked = _xor_bytes(base_digest_32, mask)
    print("Base digest: 0x"+base_digest_32[:4].hex())
    print("Mask of BPO: 0x"+mask[:4].hex())
    return "0x" + masked[:4].hex()

# --- Mainnet fork versions (CL) since Phase0 ---
MAINNET_FORK_VERSIONS = {
    "phase0":    "0x00000000",
    "altair":    "0x01000000",
    "bellatrix": "0x02000000",
    "capella":   "0x03000000",
    "deneb":     "0x04000000",
    "electra":   "0x05000000",
    "fulu":      "0x06000000",  # Fusaka / Fulu fork version (CL)
}

@dataclass(frozen=True)
class BlobScheduleEntry:
    epoch: int
    max_blobs_per_block: int

def print_mainnet_fork_digests(genesis_validators_root_hex: str) -> None:
    print("== Base fork digests (Phase0..Electra style) ==")
    for name, fv in MAINNET_FORK_VERSIONS.items():
        d = compute_fork_digest_with_bpo_mask(fv, genesis_validators_root_hex, blob_params=None)
        print(f"{name:10s} {fv}  {d}")

def print_fulu_bpo_digests(genesis_validators_root_hex: str, schedule: List[BlobScheduleEntry]) -> None:
    print("\n== Fulu digests with BPO masking (one per schedule entry) ==")
    fv = MAINNET_FORK_VERSIONS["fulu"]
    for e in schedule:
        d = compute_fork_digest_with_bpo_mask(fv, genesis_validators_root_hex, (e.epoch, e.max_blobs_per_block))
        print(f"fulu @ blob_epoch={e.epoch} max_blobs={e.max_blobs_per_block:2d}  -> {d}")

# Example usage:
genesis_root = "4b363db94e286120d76eb905340fdd4e54bfe9f06bf33ff6cf5ad27f511bfe95"
print_mainnet_fork_digests(genesis_root)

# # Example Fulu blob schedule entries (from spec page shown below)
schedule = [
    BlobScheduleEntry(epoch=412672, max_blobs_per_block=15),
    BlobScheduleEntry(epoch=419072, max_blobs_per_block=21),
]
print_fulu_bpo_digests(genesis_root, schedule)

