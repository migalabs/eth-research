import base64
from typing import Any, Dict, Tuple, List, Union

BytesLike = bytes


# ---------------------------
# Minimal RLP decoder (bytes -> python objects)
# ---------------------------
def rlp_decode(data: bytes) -> Any:
    """Decode RLP (Ethereum Recursive Length Prefix) into bytes or list."""
    obj, pos = _rlp_decode_at(data, 0)
    if pos != len(data):
        raise ValueError(f"Trailing bytes after RLP item: {len(data) - pos}")
    return obj

def _rlp_decode_at(data: bytes, pos: int) -> Tuple[Any, int]:
    if pos >= len(data):
        raise ValueError("RLP decode out of range")

    b0 = data[pos]
    # Single byte (0x00-0x7f)
    if b0 <= 0x7f:
        return bytes([b0]), pos + 1

    # Short string
    if 0x80 <= b0 <= 0xb7:
        length = b0 - 0x80
        if length == 0:
            return b"", pos + 1
        start = pos + 1
        end = start + length
        return data[start:end], end

    # Long string
    if 0xb8 <= b0 <= 0xbf:
        len_of_len = b0 - 0xb7
        start = pos + 1
        end = start + len_of_len
        length = int.from_bytes(data[start:end], "big")
        s_start = end
        s_end = s_start + length
        return data[s_start:s_end], s_end

    # Short list
    if 0xc0 <= b0 <= 0xf7:
        length = b0 - 0xc0
        start = pos + 1
        end = start + length
        items = []
        p = start
        while p < end:
            item, p = _rlp_decode_at(data, p)
            items.append(item)
        if p != end:
            raise ValueError("RLP list length mismatch (short list)")
        return items, end

    # Long list
    if 0xf8 <= b0 <= 0xff:
        len_of_len = b0 - 0xf7
        start = pos + 1
        end = start + len_of_len
        length = int.from_bytes(data[start:end], "big")
        l_start = end
        l_end = l_start + length
        items = []
        p = l_start
        while p < l_end:
            item, p = _rlp_decode_at(data, p)
            items.append(item)
        if p != l_end:
            raise ValueError("RLP list length mismatch (long list)")
        return items, l_end

    raise ValueError("Invalid RLP prefix")


# ---------------------------
# ENR decoding helpers
# ---------------------------
def _b64url_decode_nopad(s: str) -> bytes:
    # ENR uses base64url without padding; add padding if needed.
    pad = "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s + pad)

def _bytes_to_int(b: bytes) -> int:
    return int.from_bytes(b, "big") if b else 0

def _decode_ip(b: bytes) -> str:
    # 4 bytes IPv4 or 16 bytes IPv6
    if len(b) == 4:
        return ".".join(str(x) for x in b)
    if len(b) == 16:
        # very small IPv6 formatter (no compression)
        parts = [b[i:i+2].hex() for i in range(0, 16, 2)]
        return ":".join(parts)
    return b.hex()

def _try_utf8(b: bytes) -> Union[str, bytes]:
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b

def _hex0x(b: bytes) -> str:
    return "0x" + b.hex()

def _decode_eth2_forkid(v: bytes) -> Dict[str, Any]:
    """
    eth2 ForkID is typically 16 bytes:
      fork_digest(4) || next_fork_version(4) || next_fork_epoch(8)
    """
    if len(v) != 16:
        return {"raw": _hex0x(v), "note": "unexpected length"}
    fork_digest = v[0:4]
    next_fork_version = v[4:8]
    next_fork_epoch = int.from_bytes(v[8:16], "big")
    return {
        "fork_digest": "0x" + fork_digest.hex(),
        "next_fork_version": "0x" + next_fork_version.hex(),
        "next_fork_epoch": next_fork_epoch,
    }

def classify_enr(kv: Dict[str, bytes]) -> str:
    has_cl = "eth2" in kv or "attnets" in kv or "syncnets" in kv or "cgc" in kv or "nfd" in kv
    has_el = "eth" in kv or "snap" in kv or "les" in kv  # not exhaustive, but common

    if has_cl and has_el:
        return "cl+el (mixed ENR)"
    if has_cl:
        return "consensus-layer (CL)"
    if has_el:
        return "execution-layer (EL)"
    return "unknown/transport-only"

def decode_enr(enr: str) -> Dict[str, Any]:
    """
    Decode an ENR string (enr:<base64url> or enr:-<base64url>) into a dict.
    Does NOT verify the signature; it just parses.
    """
    if not enr.startswith("enr:"):
        raise ValueError("Not an ENR string (must start with 'enr:')")

    payload = enr[4:]
    raw = _b64url_decode_nopad(payload)

    rlp = rlp_decode(raw)
    if not isinstance(rlp, list) or len(rlp) < 2:
        raise ValueError("Invalid ENR RLP structure")

    signature = rlp[0]
    seq = _bytes_to_int(rlp[1])

    # Remaining items are key/value pairs: [k1, v1, k2, v2, ...]
    if (len(rlp) - 2) % 2 != 0:
        raise ValueError("Invalid ENR key/value pair count")

    kv: Dict[str, bytes] = {}
    for i in range(2, len(rlp), 2):
        k_raw = rlp[i]
        v_raw = rlp[i + 1]
        if not isinstance(k_raw, (bytes, bytearray)):
            raise ValueError("ENR keys must be bytes")
        key = k_raw.decode("utf-8", errors="strict")
        # Some ENR values (like 'snap') may be empty lists instead of empty bytes
        if isinstance(v_raw, list) and len(v_raw) == 0:
            kv[key] = b""
        elif isinstance(v_raw, (bytes, bytearray)):
            kv[key] = bytes(v_raw)
        else:
            # Store complex structures (non-empty lists) as-is for now
            kv[key] = v_raw

    # Friendly decoded view
    out: Dict[str, Any] = {
        "seq": seq,
        "signature": _hex0x(signature if isinstance(signature, (bytes, bytearray)) else b""),
        "raw_kv": {k: _hex0x(v) if isinstance(v, (bytes, bytearray)) else v for k, v in kv.items()},
    }

    # Common field decoding
    if "id" in kv:
        out["id"] = _try_utf8(kv["id"])
    if "ip" in kv:
        out["ip"] = _decode_ip(kv["ip"])
    if "ip6" in kv:
        out["ip6"] = _decode_ip(kv["ip6"])
    for p in ("udp", "tcp", "quic", "udp6", "tcp6", "quic6"):
        if p in kv:
            out[p] = _bytes_to_int(kv[p])

    if "secp256k1" in kv:
        out["secp256k1"] = _hex0x(kv["secp256k1"])
    if "eth2" in kv:
        out["eth2"] = _decode_eth2_forkid(kv["eth2"])
    if "nfd" in kv:  # next fork digest (often 4 bytes)
        out["nfd"] = _hex0x(kv["nfd"])
    if "attnets" in kv:
        out["attnets"] = _hex0x(kv["attnets"])
    if "syncnets" in kv:
        out["syncnets"] = _hex0x(kv["syncnets"])
    if "cgc" in kv:  # custody group count (PeerDAS/Fulu)
        out["cgc"] = _bytes_to_int(kv["cgc"])

    # Anything else: show as hex, and as utf8 if printable
    extras = {}
    for k, v in kv.items():
        if k in {"id","ip","ip6","udp","tcp","quic","udp6","tcp6","quic6","secp256k1","eth2","nfd","attnets","syncnets","cgc"}:
            continue
        if isinstance(v, (bytes, bytearray)):
            extras[k] = {
                "hex": _hex0x(v),
                "utf8": _try_utf8(v) if isinstance(_try_utf8(v), str) else None,
                "int": _bytes_to_int(v) if len(v) <= 8 else None,
            }
        else:
            extras[k] = {"value": v}
    if extras:
        out["extras"] = extras

    out["role_guess"] = classify_enr(kv)

    return out


# ---------------------------
# Example usage
# ---------------------------
if __name__ == "__main__":
    enr_str = "enr:-Ni4QKhc2sAPhDkXl5rVVIuAZnuJeXbGA4d0EYnj85voGWrOPnHZfloqz3xSDTg-wkpqFIij_X6V5rEZsk0EH_vfuk2GAZpyK7Jlh2F0dG5ldHOIAAYAAAAAAACDY2djBIRldGgykMsNGswGAAAAAGUGAAAAAACCaWSCdjSCaXCEW9JlLYNuZmSEjJ9i_oRxdWljgjLIiXNlY3AyNTZrMaED7bfniNwFhVLo9Kq2wTs4kAUBBPcV0sF4OWH3tgjDehqIc3luY25ldHMAg3RjcIIyyIN1ZHCCLuA"
    decoded = decode_enr(enr_str)
    from pprint import pprint
    pprint(decoded)

    enr_str = "enr:-J24QG3pjTFObcDvTOTJr2qPOTDH3-YxDqS47Ylm-kgM5BUwb1oD5Id6fSRTfUzTahTa7y4TWx_HSV7wri7T6iYtyAQHg2V0aMfGhLjGKZ2AgmlkgnY0gmlwhJ1a19CJc2VjcDI1NmsxoQPlCNb7N__vcnsNC8YYkFkmNj8mibnR5NuvSowcRZsLU4RzbmFwwIN0Y3CCdl-DdWRwgnZf"
    decoded = decode_enr(enr_str)
    from pprint import pprint
    pprint(decoded)



