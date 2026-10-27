"""
PMS Enterprise Security & Defense-in-Depth Package.

Provides production-grade AI security controls:
1. Guardrails: Anti-Prompt Injection, Canary Honeytokens, PII & IP Redaction, Input Sanitization.
2. Gateway: Security HTTP Headers, Strict CORS, Request Boundary Protection.
3. Circuit Breaker: Multi-Provider AI Resiliency, Failover, Degradation Handling.
4. Audit: Cryptographically Chained Immutable Audit Trails (SOC 2 / ISO 27001).
5. Model Integrity: SHA-256 Checksum Verification & Anti-Poisoning Protection.
"""

from backend.security.guardrails import (
    CanaryTrap,
    InputSanitizer,
    PIISanitizer,
    PromptShield,
)
from backend.security.circuit_breaker import (
    AICircuitBreaker,
    AIFailoverManager,
    CircuitState,
    get_circuit_breaker,
    get_failover_manager,
)
from backend.security.audit import (
    AuditEvent,
    AuditLogger,
    get_audit_logger,
)
from backend.security.gateway import (
    EnterpriseSecurityHeadersMiddleware,
    configure_enterprise_cors,
)
from backend.security.model_integrity import (
    KNOWN_PRODUCTION_MODEL_SHA256,
    ModelIntegrityVerifier,
)
from backend.security.idempotency import (
    IdempotencyManager,
    IdempotencyRecord,
    get_idempotency_manager,
)

__all__ = [
    "InputSanitizer",
    "PromptShield",
    "CanaryTrap",
    "PIISanitizer",
    "AICircuitBreaker",
    "AIFailoverManager",
    "CircuitState",
    "get_circuit_breaker",
    "get_failover_manager",
    "AuditEvent",
    "AuditLogger",
    "get_audit_logger",
    "EnterpriseSecurityHeadersMiddleware",
    "configure_enterprise_cors",
    "ModelIntegrityVerifier",
    "KNOWN_PRODUCTION_MODEL_SHA256",
    "IdempotencyManager",
    "IdempotencyRecord",
    "get_idempotency_manager",
]
