from __future__ import annotations

import importlib
import os
import py_compile
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = [
    "app/main.py",
    "app/core/config.py",
    "app/core/schema_catalog.py",
    "app/core/sql_guard.py",
    "app/db/session.py",
    "app/services/schema_context.py",
    "app/services/query_executor.py",
    "app/services/gemini_service.py",
    "app/services/assistant.py",
    "app/api/routes/ask.py",
    "app/templates/index.html",
    "app/static/css/insightpilot.css",
    "app/static/js/insightpilot.js",
    "data/sql/schema.sql",
    "data/sql/readonly_role.sql",
    "data/sql/load_seed_data.sql",
    "tests",
    "requirements.txt",
    ".env",
]

CORE_IMPORTS = [
    "fastapi",
    "sqlalchemy",
    "psycopg",
    "pydantic_settings",
    "sqlglot",
    "google.genai",
    "jinja2",
]


def ok(message: str) -> None:
    print(f"[PASS] {message}")


def warn(message: str) -> None:
    print(f"[WARN] {message}")


def fail(message: str) -> None:
    print(f"[FAIL] {message}")


def section(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def check_project_structure() -> bool:
    section("1. PROJECT STRUCTURE")
    success = True

    for relative in REQUIRED_PATHS:
        path = PROJECT_ROOT / relative
        if path.exists():
            ok(relative)
        else:
            fail(f"Missing: {relative}")
            success = False

    return success


def check_python_syntax() -> bool:
    section("2. PYTHON SYNTAX")
    success = True

    for py_file in (PROJECT_ROOT / "app").rglob("*.py"):
        try:
            py_compile.compile(str(py_file), doraise=True)
        except Exception as exc:
            fail(f"{py_file.relative_to(PROJECT_ROOT)} -> {exc}")
            success = False

    if success:
        ok("All Python files under app/ compile successfully.")

    return success


def check_dependencies() -> bool:
    section("3. CORE DEPENDENCIES")
    success = True

    for module_name in CORE_IMPORTS:
        try:
            importlib.import_module(module_name)
            ok(module_name)
        except Exception as exc:
            fail(f"{module_name}: {type(exc).__name__}: {exc}")
            success = False

    return success


def check_configuration() -> bool:
    section("4. CONFIGURATION PRESENCE")

    try:
        from app.core.config import settings
    except Exception as exc:
        fail(f"Could not import settings: {type(exc).__name__}: {exc}")
        return False

    db_present = bool(
        getattr(settings, "database_url", None)
        or getattr(settings, "db_url", None)
        or getattr(settings, "postgres_url", None)
    )

    if not db_present:
        db_present = any(
            getattr(settings, name, None)
            for name in (
                "db_host",
                "db_port",
                "db_name",
                "db_user",
                "db_password",
                "database_name",
                "database_user",
                "database_password",
            )
        )

    if db_present:
        ok("Database configuration present")
    else:
        warn("Database configuration not detected by generic regression script")

    if getattr(settings, "gemini_api_key", None):
        ok("Gemini API key present")
    else:
        warn("Gemini API key not detected")

    if getattr(settings, "gemini_model", None):
        ok("Gemini model configured")
    else:
        warn("Gemini model not detected")

    # These are presence checks only; warnings are not regression blockers.
    return True


def check_app_endpoints() -> bool:
    section("5. FASTAPI ENDPOINT REGRESSION")
    success = True

    try:
        from fastapi.testclient import TestClient
        from app.main import app
    except Exception as exc:
        fail(f"Could not import FastAPI app: {type(exc).__name__}: {exc}")
        return False

    client = TestClient(app)

    # Root status
    response = client.get("/")
    if response.status_code == 200:
        ok("GET / -> 200")
    else:
        fail(f"GET / -> {response.status_code}")
        success = False

    # UI render
    response = client.get("/ui")
    if response.status_code == 200 and "InsightPilot" in response.text:
        ok("GET /ui -> 200 and UI rendered")
    else:
        fail(f"GET /ui -> {response.status_code}")
        success = False

    # Schema context
    response = client.post(
        "/api/v1/schema/context",
        json={"question": "What was total revenue last month?"},
    )
    if response.status_code == 200:
        ok("POST /api/v1/schema/context -> 200")
    else:
        fail(
            "POST /api/v1/schema/context -> "
            f"{response.status_code}: {response.text[:180]}"
        )
        success = False

    # SQL validation
    safe_payload = {
        "question": "Read customers safely.",
        "sql": "SELECT customer_id FROM customers LIMIT 5",
    }

    response = client.post("/api/v1/query/validate", json=safe_payload)
    if response.status_code == 200:
        ok("POST /api/v1/query/validate -> 200")
    else:
        fail(
            "POST /api/v1/query/validate -> "
            f"{response.status_code}: {response.text[:180]}"
        )
        success = False

    # Read-only DB execution
    response = client.post("/api/v1/query/execute", json=safe_payload)
    if response.status_code == 200:
        ok("POST /api/v1/query/execute -> 200 (read-only DB path)")
    else:
        fail(
            "POST /api/v1/query/execute -> "
            f"{response.status_code}: {response.text[:180]}"
        )
        success = False

    # Unsupported question must stop before Gemini/DB investigation.
    response = client.post(
        "/api/v1/ask",
        json={"question": "Will tomorrow be a lucky day for me?"},
    )
    if response.status_code == 422:
        ok("POST /api/v1/ask unsupported question -> 422 as expected")
    else:
        fail(
            "Unsupported-question check expected 422, "
            f"got {response.status_code}"
        )
        success = False

    return success


def run_pytest() -> bool:
    section("6. FULL AUTOMATED TEST SUITE")

    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=PROJECT_ROOT,
    )

    if completed.returncode == 0:
        ok("Full pytest suite passed.")
        return True

    fail(f"pytest exited with code {completed.returncode}")
    return False


def secret_hygiene_precheck() -> bool:
    section("7. PRE-GIT SECRET HYGIENE")
    success = True

    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        ok(".env exists locally (contents intentionally not printed).")
    else:
        fail(".env is missing.")
        success = False

    example_path = PROJECT_ROOT / ".env.example"
    if example_path.exists():
        ok(".env.example exists.")
    else:
        warn(".env.example not found.")

    gitignore_path = PROJECT_ROOT / ".gitignore"
    if not gitignore_path.exists():
        warn(".gitignore not created yet — expected before Git initialization.")
        return success

    gitignore = gitignore_path.read_text(encoding="utf-8", errors="ignore")
    if ".env" in gitignore:
        ok(".gitignore protects .env")
    else:
        fail(".gitignore exists but does not appear to ignore .env")
        success = False

    return success


def main() -> int:
    os.chdir(PROJECT_ROOT)

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    print("InsightPilot AI — V1 Final Regression (Day 4 Fix)")
    print(f"Project: {PROJECT_ROOT}")
    print("Secrets will not be printed.")
    print("Only read-only database execution is performed.")

    results = [
        check_project_structure(),
        check_python_syntax(),
        check_dependencies(),
        check_configuration(),
        check_app_endpoints(),
        run_pytest(),
        secret_hygiene_precheck(),
    ]

    section("FINAL RESULT")

    if all(results):
        print("[PASS] V1 automated final regression PASSED.")
        print("Next gate: V1 documentation.")
        return 0

    print("[FAIL] V1 automated final regression has one or more blockers.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
