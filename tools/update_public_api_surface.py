from __future__ import annotations

import argparse
from pathlib import Path

from validate_public_api_surface import update_public_api_surface

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update the committed public API surface file.")
    parser.parse_args(argv)

    try:
        path = update_public_api_surface(ROOT)
    except ValueError as exc:
        print(str(exc))
        return 1
    print(f"Updated {path.relative_to(ROOT).as_posix()}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
