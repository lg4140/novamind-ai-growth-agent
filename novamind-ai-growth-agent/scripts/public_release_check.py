"""Fail closed on common accidental public-repository leaks and stale bundles."""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISALLOWED_DIRS = {"legacy", "deliverables", ".venv", "venv", "__pycache__", ".git"}
DISALLOWED_FILES = {".env", "plan.json"}
DISALLOWED_SUFFIXES = {".zip", ".db", ".sqlite", ".sqlite3", ".pem", ".p12", ".pfx", ".key", ".docx"}
SOURCE_EXTS = {".py", ".md", ".txt", ".csv", ".yml", ".yaml", ".toml", ".ini", ".jsonl"}


def main():
    errors = []
    for f in ROOT.rglob("*"):
        if not f.is_file():
            continue
        parts = set(f.relative_to(ROOT).parts)
        if any(x in parts for x in DISALLOWED_DIRS):
            # Git metadata/temporary interpreter caches may legitimately exist locally.
            continue
        if f.name in DISALLOWED_FILES or f.suffix.lower() in DISALLOWED_SUFFIXES or f.name.startswith('.env.') and f.name != '.env.example':
            errors.append(f"Unexpected runtime/binary/secret file: {f.relative_to(ROOT)}")
            continue
        if f.resolve() == Path(__file__).resolve():
            continue  # Checker contains literal detection signatures, not actual secrets.
        if f.suffix.lower() in SOURCE_EXTS or f.name in {'.env.example','.gitignore','.gitattributes'}:
            data = f.read_text(encoding='utf-8', errors='replace')
            for phrase in ('-----BEGIN PRIVATE KEY-----', '-----BEGIN OPENSSH PRIVATE KEY-----'):
                if phrase in data:
                    errors.append(f"Private key marker: {f.relative_to(ROOT)}")
            # Scan for OpenAI key-like strings without rejecting documentation that
            # simply mentions OPENAI_API_KEY as an environment variable.
            if re.search(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}', data):
                errors.append(f"Potential API key: {f.relative_to(ROOT)}")
    with (ROOT / "data" / "contacts.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        errors.append("Demo contacts fixture is empty")
    if any(not x["email"].lower().endswith("@example.com") for x in rows):
        errors.append("Demo CSV contains an address outside the reserved example.com domain")
    if (ROOT / "legacy").exists() or (ROOT / "deliverables").exists():
        errors.append("Private archives or binary handouts should not be in the public repository")
    if errors:
        raise SystemExit("PUBLIC RELEASE CHECK FAILED:\n" + "\n".join(errors))
    print(f"PUBLIC RELEASE CHECK: PASS — {len(rows)} fictional example.com contacts, no obvious secret artifacts")


if __name__ == "__main__":
    main()
