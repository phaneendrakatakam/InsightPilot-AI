from __future__ import annotations

import py_compile
import re
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


ROOT = Path(__file__).resolve().parents[1]

SAFE_SECRET_PATTERNS = {
    "possible Google API key": re.compile(r"\bAIza[0-9A-Za-z\-_]{30,}\b"),
    "possible GitHub token": re.compile(r"\bgh[pousr]_[0-9A-Za-z]{30,}\b"),
    "possible generic bearer token": re.compile(
        r"(?i)\b(?:authorization|bearer)\b.{0,12}[=:]\s*['\"]?[A-Za-z0-9._\-]{24,}"
    ),
    "possible hardcoded password": re.compile(
        r"(?i)\b(?:db_password|database_password|password)\s*=\s*['\"][^'\"]{6,}['\"]"
    ),
}

TEXT_SUFFIXES = {
    ".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml",
    ".html", ".css", ".js", ".sql", ".ini", ".cfg", ".example",
}

FORBIDDEN_TRACKED_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
}


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=capture,
        check=False,
    )


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(1)


def pass_line(message: str) -> None:
    print(f"[PASS] {message}")


def tracked_files() -> list[Path]:
    result = run(["git", "ls-files"], capture=True)
    if result.returncode != 0:
        fail("Could not read Git tracked files.")
    return [ROOT / line for line in result.stdout.splitlines() if line.strip()]


def check_branch() -> None:
    result = run(["git", "branch", "--show-current"], capture=True)
    branch = result.stdout.strip()
    if branch != "V2":
        fail(f"Expected current branch V2, found {branch or 'unknown'}.")
    pass_line("Current branch is V2.")


def check_worktree_status() -> None:
    result = run(["git", "status", "--short"], capture=True)
    if result.returncode != 0:
        fail("Could not inspect Git worktree.")

    dirty = result.stdout.strip()
    if dirty:
        print("[INFO] Worktree has uncommitted V2 changes:")
        print(dirty)
    else:
        pass_line("Git worktree is clean.")


def check_tracked_sensitive_files(files: list[Path]) -> None:
    bad = []
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        if path.name in FORBIDDEN_TRACKED_NAMES:
            bad.append(rel)

    if bad:
        fail("Sensitive environment file(s) are tracked: " + ", ".join(bad))

    pass_line("No sensitive .env files are tracked.")


def check_secret_patterns(files: list[Path]) -> None:
    findings: list[str] = []

    for path in files:
        if not path.is_file():
            continue

        if path.name == ".env.example":
            continue

        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {
            "Dockerfile", "README", "LICENSE"
        }:
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for label, pattern in SAFE_SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{path.relative_to(ROOT).as_posix()}: {label}")

    if findings:
        print("[FAIL] Potential secret-like values found. Values are intentionally not printed.")
        for finding in findings:
            print(f"  - {finding}")
        raise SystemExit(1)

    pass_line("No obvious hardcoded secret patterns found in tracked text files.")


def check_python_compilation() -> None:
    targets = [ROOT / "app", ROOT / "tests", ROOT / "scripts"]
    failures: list[str] = []

    for target in targets:
        if not target.exists():
            continue

        for path in target.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            try:
                py_compile.compile(str(path), doraise=True)
            except py_compile.PyCompileError:
                failures.append(path.relative_to(ROOT).as_posix())

    if failures:
        fail("Python compilation failed: " + ", ".join(failures))

    pass_line("Python compilation passed.")


def check_routes_and_ui() -> None:
    client = TestClient(app)

    root_response = client.get("/")
    if root_response.status_code != 200:
        fail(f"/ returned HTTP {root_response.status_code}.")

    content_type = root_response.headers.get("content-type", "")
    if "text/html" not in content_type:
        fail("/ is not serving the product UI.")

    body = root_response.text
    required_ui_markers = [
        "InsightPilot",
        "V2 · Investigation Agent",
        "Multi-step enterprise investigation",
        "Investigation trail",
    ]
    for marker in required_ui_markers:
        if marker not in body:
            fail(f'Root UI is missing expected marker: "{marker}".')

    ui_alias = client.get("/ui")
    if ui_alias.status_code != 200:
        fail(f"/ui alias returned HTTP {ui_alias.status_code}.")

    openapi = client.get("/openapi.json")
    if openapi.status_code != 200:
        fail("OpenAPI schema could not be loaded.")

    paths = openapi.json().get("paths", {})
    required_paths = {
        "/api/v1/health",
        "/api/v1/schema/context",
        "/api/v1/query/validate",
        "/api/v1/query/execute",
        "/api/v1/ask",
        "/api/v2/investigate",
    }

    missing = sorted(required_paths - set(paths))
    if missing:
        fail("Required API route(s) missing: " + ", ".join(missing))

    pass_line("Root UI, /ui alias, V1 routes, and V2 investigate route are registered.")


def run_pytest() -> None:
    print("\n=== Full pytest regression ===")
    result = run([sys.executable, "-m", "pytest", "-q"])
    if result.returncode != 0:
        fail("pytest regression failed.")
    pass_line("Full pytest regression passed.")


def main() -> None:
    print("=== InsightPilot AI V2 — Day 6 Release Audit ===\n")

    check_branch()
    check_worktree_status()

    files = tracked_files()
    check_tracked_sensitive_files(files)
    check_secret_patterns(files)
    check_python_compilation()
    check_routes_and_ui()
    run_pytest()

    print("\n[PASS] V2 release audit completed successfully.")
    print("Next: version freeze, README V2, screenshots, Git release.")


if __name__ == "__main__":
    main()
