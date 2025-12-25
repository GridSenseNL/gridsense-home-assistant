import json
import sys
from pathlib import Path

p = Path("custom_components/gridsense/manifest.json")
if not p.exists():
    print(f"ERROR: manifest not found at {p}")
    sys.exit(2)

try:
    m = json.loads(p.read_text())
except Exception as e:
    print("ERROR: cannot parse manifest.json:", e)
    sys.exit(2)

required = ("domain", "name", "documentation")
missing = [k for k in required if k not in m]
if missing:
    print("MISSING KEYS:", missing)
    sys.exit(1)

print("MANIFEST OK")
sys.exit(0)
