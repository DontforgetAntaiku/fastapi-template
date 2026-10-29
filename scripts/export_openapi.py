import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.utils.openapi import typescript_compatible
from main import app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("-o", "--output", default="openapi.json")
    parser.add_argument(
        "--typescript",
        action="store_true",
        help="OpenAPI 3.1 where QUERY operations become POST '<path>::QUERY'",
    )
    args = parser.parse_args()

    spec = app.openapi()
    if args.typescript:
        spec = typescript_compatible(spec)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(spec, indent=2) + "\n")
    print(f"wrote {args.output} (openapi {spec['openapi']})")


if __name__ == "__main__":
    main()
