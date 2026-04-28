"""
Reads data/use_cases.csv and renders template.html → index.html.
Run locally:  python scripts/generate.py
Run in CI:    same command, no arguments needed.
"""
import csv, io, json, re, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

COLUMN_MAP = {
    "id":        "ID",
    "cat":       "Category",
    "vert":      "Vertical",
    "prods":     "Products",
    "prob":      "Problem / Use Case Title",
    "trigger":   "Buying Trigger",
    "challenge": "Customer Challenge",
    "solution":  "How Keysight Solves It",
    "caps":      "Technical Capabilities",
    "outcome":   "Business Outcome",
}

COMMA_SPLIT = {"prods", "caps"}

PLACEHOLDER = "/*USE_CASES_DATA_PLACEHOLDER*/[]/*END_USE_CASES_DATA*/"


def unwrap(raw: str) -> str:
    """
    Power Automate wraps the CSV in a JSON envelope: {"body":"<escaped csv>"}.
    This function strips that envelope and returns the plain CSV string.
    """
    stripped = raw.lstrip('﻿').strip()  # remove BOM and whitespace

    if not stripped.startswith('{"body":"'):
        return stripped  # not wrapped, return as-is

    print("Detected Power Automate JSON wrapper — extracting CSV body...")

    # Method 1: json.loads on the full envelope
    try:
        parsed = json.loads(stripped)
        csv_str = parsed["body"]
        print(f"json.loads unwrap succeeded ({len(csv_str)} chars)")
        return csv_str
    except Exception as e:
        print(f"json.loads failed ({e}), trying regex extraction...")

    # Method 2: regex extraction + manual JSON string unescaping
    try:
        # Extract everything between the opening {"body":" and the closing "}
        m = re.search(r'^{"body":"(.*)"}\s*$', stripped, re.DOTALL)
        if m:
            inner = m.group(1)
            # Decode JSON escape sequences manually
            inner = inner.replace('\\r\\n', '\r\n')
            inner = inner.replace('\\n', '\n')
            inner = inner.replace('\\r', '\r')
            inner = inner.replace('\\"', '"')
            inner = inner.replace('\\\\', '\\')
            print(f"Regex unwrap succeeded ({len(inner)} chars)")
            return inner
    except Exception as e:
        print(f"Regex extraction failed ({e})")

    print("WARNING: Could not unwrap — using raw content")
    return stripped


def load_use_cases(csv_path: Path) -> list[dict]:
    raw = csv_path.read_text(encoding="utf-8-sig")
    csv_text = unwrap(raw)

    reader = csv.DictReader(io.StringIO(csv_text))
    print(f"CSV columns: {list(reader.fieldnames)}")

    use_cases = []
    for row in reader:
        id_raw = (row.get("ID") or "").strip()
        if not id_raw.isdigit():
            continue
        entry = {}
        for key, col in COLUMN_MAP.items():
            value = (row.get(col) or "").strip()
            if key in COMMA_SPLIT:
                entry[key] = [v.strip() for v in value.split(",") if v.strip()]
            elif key == "id":
                entry[key] = int(value)
            else:
                entry[key] = value
        use_cases.append(entry)
    return use_cases


def main():
    csv_path      = ROOT / "data" / "use_cases.csv"
    template_path = ROOT / "template.html"
    output_path   = ROOT / "index.html"

    use_cases = load_use_cases(csv_path)

    if not use_cases:
        print("ERROR: No use cases loaded — aborting to avoid wiping the site.", file=sys.stderr)
        sys.exit(1)

    template = template_path.read_text(encoding="utf-8")

    assert PLACEHOLDER in template, (
        "Placeholder not found in template.html — "
        "ensure the file contains: " + PLACEHOLDER
    )

    output = template.replace(PLACEHOLDER, json.dumps(use_cases, indent=2))
    output_path.write_text(output, encoding="utf-8")

    print(f"Generated index.html with {len(use_cases)} use cases.")


if __name__ == "__main__":
    main()
