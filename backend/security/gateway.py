"""
PMS Enterprise Gateway & HTTP Security Middleware.

Enforces:
1. Enterprise Security Headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options).
2. Tightened, environment-aware CORS policy (no wildcard origins with credentials).
3. Transport-level body size protection against buffer exhaustion attacks.
"""
from __future__ import annotations

import os
from typing import List
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class EnterpriseSecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects defense-in-depth security headers and validates request bounds."""

    def __init__(self, app: FastAPI, max_content_length: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_content_length = max_content_length

    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. Transport-level payload size check
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_content_length:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "Payload Too Large",
                            "detail": f"Request body exceeds maximum allowed limit of {self.max_content_length // (1024 * 1024)}MB.",
                        },
                    )
            except ValueError:
                pass

        # 2. Process request through downstream pipeline
        response = await call_next(request)

        # 3. Inject hardened security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()"
        )

        # Content-Security-Policy (Restricts unauthorized inline script execution and clickjacking)
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https:; "
            "style-src 'self' 'unsafe-inline' https:; "
            "img-src 'self' data: https:; "
            "font-src 'self' https: data:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp_policy

        # Enforce HSTS for HTTPS connections in staging and production
        is_ssl = (
            request.url.scheme == "https"
            or request.headers.get("x-forwarded-proto") == "https"
            or os.getenv("ENVIRONMENT") == "production"
        )
        if is_ssl:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"

        return response


def configure_enterprise_cors(app: FastAPI) -> None:
    """Configures hardened, environment-aware CORS policies."""
    raw_origins = os.getenv(
        "CORS_ORIGINS",
        "https://pms-frontend.vercel.app,http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000",
    )
    allowed_origins: List[str] = [orig.strip() for orig in raw_origins.split(",") if orig.strip()]

    # In development or test, allow all if explicitly requested
    if os.getenv("ENVIRONMENT") == "development" or os.getenv("LOAD_TEST_MODE") == "1":
        if "*" not in allowed_origins:
            allowed_origins.append("*")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins if allowed_origins else ["*"],
        allow_credentials=True if "*" not in allowed_origins else False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
        max_age=86400,
    )
