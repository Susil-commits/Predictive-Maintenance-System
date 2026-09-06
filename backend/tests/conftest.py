import os

# Pytest executes conftest.py before collecting test modules.
# Ensure required environment variables have valid test values before backend.main
# runs its startup validation (validate_startup_env).
FALLBACK_TEST_ENV = {
    "DATABASE_URL": "sqlite:///./pms.db",
    "PMS_API_KEY": "pms-test-api-key-ci",
    "ADMIN_USERNAME": "admin",
    "ADMIN_PASSWORD": "PmsAdmin#Secure2026!",
    "JWT_SECRET": "pms-test-jwt-secret-signing-key-32chars-minimum",
}

for var_name, default_val in FALLBACK_TEST_ENV.items():
    val = os.getenv(var_name)
    if not val or not val.strip():
        os.environ[var_name] = default_val
