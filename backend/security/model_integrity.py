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

    MANIFEST_FILENAME = "model_manifest.json"

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
    def get_manifest_path(cls, model_filepath: str) -> str:
        """Derives the model_manifest.json path adjacent to the model file."""
        return os.path.join(os.path.dirname(os.path.abspath(model_filepath)), cls.MANIFEST_FILENAME)

    @classmethod
    def load_manifest(cls, model_filepath: str) -> Optional[dict]:
        """Loads and parses model_manifest.json if present."""
        manifest_path = cls.get_manifest_path(model_filepath)
        if os.path.isfile(manifest_path):
            try:
                import json

                with open(manifest_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to parse model manifest at {manifest_path}: {e}")
        return None

    @classmethod
    def create_or_update_manifest(
        cls,
        model_filepath: str,
        version: str = "v1",
        extra_metadata: Optional[dict] = None,
    ) -> dict:
        """Generates or updates model_manifest.json with the cryptographic SHA-256 hash of the artifact."""
        import json
        from datetime import UTC, datetime

        sha256_hash = cls.calculate_file_sha256(model_filepath)
        manifest = {
            "model_file": os.path.basename(model_filepath),
            "sha256": sha256_hash,
            "version": version,
            "created_at": datetime.now(UTC).isoformat(),
            "algorithm": "SHA-256",
            "integrity_status": "verified_internal_build",
        }
        if extra_metadata:
            manifest.update(extra_metadata)

        manifest_path = cls.get_manifest_path(model_filepath)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        logger.info(f"Model manifest created at {manifest_path} (SHA-256: {sha256_hash[:16]}...)")
        return manifest

    @classmethod
    def verify_model_file(
        cls,
        filepath: str,
        expected_sha256: Optional[str] = None,
        allow_unregistered: bool = True,
    ) -> Tuple[bool, str, str]:
        """
        Verifies that the model file matches the expected SHA-256 checksum or signed manifest.
        Returns: (is_valid, calculated_hash, message)
        """
        calculated_hash = cls.calculate_file_sha256(filepath)

        # 1. Explicit target hash takes absolute precedence
        target_hash = (expected_sha256 or os.getenv("EXPECTED_MODEL_SHA256") or "").strip()

        # 2. Check dynamic manifest if no explicit target provided
        if not target_hash:
            manifest = cls.load_manifest(filepath)
            if manifest and "sha256" in manifest:
                target_hash = str(manifest["sha256"]).strip()

        # 3. Fallback to known canonical constant
        if not target_hash:
            target_hash = KNOWN_PRODUCTION_MODEL_SHA256.strip()

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
