#!/usr/bin/env python3
"""Load initial supplier records into TinyDB."""

from __future__ import annotations

from suppliers.repository import seed_suppliers


def main() -> int:
    added, skipped = seed_suppliers()
    print(f"Seed complete: added {added} supplier(s), skipped {skipped} duplicate(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
