"""Independently verify a sealed admission/qualification evidence directory."""

import argparse
import json
from .integrity import verify_bundle


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory")
    args = p.parse_args()
    result = verify_bundle(args.directory)
    print(
        json.dumps(
            {
                "status": "VERIFIED",
                "qualification": result.get("qualification"),
                "git_head": result.get("git_head"),
                "capability_status": result["capability_status"],
            }
        )
    )


if __name__ == "__main__":
    main()
