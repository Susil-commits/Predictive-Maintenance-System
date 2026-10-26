"""
PMS Model Artifact Integrity & Anti-Tampering Engine.

Guarantees:
1. Every machine learning model artifact (.pkl / .joblib) is cryptographically verified
   via SHA-256 before deserialization.
2. Defends against model poisoning, unverified artifact substitution, and deserialization attacks.
"""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
from typing import Optional, Tuple

logger = logging.getLogger("pms.security.model_integrity")

# Canonical SHA-256 checksum for the verified production calibrated XGBoost model
KNOWN_PRODUCTION_MODEL_SHA256 = "8ea68fbb817301a37b4f8d917e8826238e801fa6e4529241f35ba282f0a01d78"


class ModelIntegrityVerifier:
    """Verifies cryptographic integrity of machine learning model files prior to loading."""

    @classmethod
    def calculate_file_sha256(cls, filepath: str) -> str:
        """Calculates deterministic SHA-256 hash of a file on disk."""
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"Model file not found: {filepath}")

        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @classmethod
    def verify_model_file(
        cls,
        filepath: str,
        expected_sha256: Optional[str] = None,
        allow_unregistered: bool = True,
    ) -> Tuple[bool, str, str]:
        """
        Verifies that the model file matches the expected SHA-256 checksum.
        Returns: (is_valid, calculated_hash, message)
        """
        calculated_hash = cls.calculate_file_sha256(filepath)
        target_hash = (expected_sha256 or os.getenv("EXPECTED_MODEL_SHA256") or KNOWN_PRODUCTION_MODEL_SHA256).strip()

        if not target_hash:
            if allow_unregistered:
                return True, calculated_hash, "Model loaded without pinned checksum (verification optional)."
            return False, calculated_hash, "No reference checksum configured for strict model verification."

        # Constant-time comparison to prevent timing side channels
        if secrets.compare_digest(calculated_hash.lower(), target_hash.lower()):
            return True, calculated_hash, "Cryptographic integrity verified: model checksum matches reference."

        err_msg = (
            f"SECURITY ALERT: Model artifact checksum mismatch! "
            f"Calculated: {calculated_hash} != Expected: {target_hash}"
        )
        logger.error(err_msg)
        return False, calculated_hash, err_msg
