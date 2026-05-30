import hashlib


def calcular_sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
