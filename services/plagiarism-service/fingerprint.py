"""Fingerprinting de codigo: k-gram + winnowing -> similitud Jaccard (inciso III).

Winnowing (Schleimer et al.): se trocea el codigo en k-gramas, se hashea cada uno
y, en una ventana deslizante de tamano w, se conserva el hash minimo. El conjunto
de minimos es la huella; comparar huellas con Jaccard resiste reordenamientos y
reformateos triviales.
"""
from __future__ import annotations

import hashlib

K_GRAM = 5    # tamano del k-grama
WINDOW = 4    # tamano de la ventana de winnowing


def _normalize(code: str) -> str:
    """Quita todo el espacio en blanco para resistir reformateos triviales."""
    return "".join(code.split())


def _kgrams(text: str, k: int) -> list[str]:
    if len(text) < k:
        return [text] if text else []
    return [text[i:i + k] for i in range(len(text) - k + 1)]


def _hash(gram: str) -> int:
    return int(hashlib.sha1(gram.encode("utf-8")).hexdigest(), 16)


def fingerprint(code: str, k: int = K_GRAM, w: int = WINDOW) -> set[int]:
    """Conjunto de huellas de un fragmento de codigo (winnowing)."""
    hashes = [_hash(g) for g in _kgrams(_normalize(code), k)]
    if not hashes:
        return set()
    if len(hashes) < w:
        return {min(hashes)}
    return {min(hashes[i:i + w]) for i in range(len(hashes) - w + 1)}


def jaccard(a: set[int], b: set[int]) -> float:
    """Similitud Jaccard entre dos conjuntos de huellas (0.0 - 1.0)."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
