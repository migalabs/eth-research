import hashlib

def compute_fork_digest(fork_version_hex: str, genesis_validators_root_hex: str) -> str:
    """
    Ethereum CL fork digest = first 4 bytes of SSZ hash_tree_root(ForkData)
    ForkData(current_version: Bytes4, genesis_validators_root: Bytes32)

    Returns hex string with 0x prefix (8 hex chars / 4 bytes).
    """
    fv = bytes.fromhex(fork_version_hex.removeprefix("0x"))
    gvr = bytes.fromhex(genesis_validators_root_hex.removeprefix("0x"))

    if len(fv) != 4:
        raise ValueError("fork_version must be exactly 4 bytes (8 hex chars).")
    if len(gvr) != 32:
        raise ValueError("genesis_validators_root must be exactly 32 bytes (64 hex chars).")

    # SSZ chunking: Bytes4 is right-padded with zeros to 32 bytes
    chunk0 = fv + b"\x00" * 28
    chunk1 = gvr

    fork_data_root = hashlib.sha256(chunk0 + chunk1).digest()  # 2 chunks => single sha256
    digest = fork_data_root[:4]
    return "0x" + digest.hex()


# --- Mainnet fork versions (consensus-specs mainnet config) ---
MAINNET_FORK_VERSIONS = {
    "phase0":    "0x00000000",  # GENESIS_FORK_VERSION :contentReference[oaicite:2]{index=2}
    "altair":    "0x01000000",  # ALTAIR_FORK_VERSION :contentReference[oaicite:3]{index=3}
    "bellatrix": "0x02000000",  # BELLATRIX_FORK_VERSION :contentReference[oaicite:4]{index=4}
    "capella":   "0x03000000",  # CAPELLA_FORK_VERSION :contentReference[oaicite:5]{index=5}
    "deneb":     "0x04000000",  # DENEB_FORK_VERSION :contentReference[oaicite:6]{index=6}
    "electra":   "0x05000000",  # ELECTRA_FORK_VERSION :contentReference[oaicite:7]{index=7}
    "fulu":      "0x06000000",  # FULU_FORK_VERSION :contentReference[oaicite:7]{index=7}
}

# Example usage:
genesis_root = "0x4b363db94e286120d76eb905340fdd4e54bfe9f06bf33ff6cf5ad27f511bfe95" # Mainnet
for name, v in MAINNET_FORK_VERSIONS.items():
    print(name, v, compute_fork_digest(v, genesis_root))

