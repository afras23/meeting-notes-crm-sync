"""
CLI entrypoint for meeting extraction evaluation.

Loads ``eval/test_set.jsonl`` by default and writes a JSON report under ``eval/results/``.
"""

# Standard library
from __future__ import annotations

import argparse
import asyncio
import json
import logging

# Local
from eval.evaluate import run_evaluation

logger = logging.getLogger(__name__)


async def _async_main() -> None:
    parser = argparse.ArgumentParser(description="Run meeting extraction evaluation.")
    parser.add_argument(
        "--test-set",
        default="eval/test_set.jsonl",
        help="Path to JSONL test set.",
    )
    parser.add_argument(
        "--output",
        default="eval/results",
        help="Output JSON file path, or directory for eval_YYYY-MM-DD.json.",
    )
    args = parser.parse_args()
    report = await run_evaluation(args.test_set, args.output)
    logger.info("evaluation_complete %s", json.dumps(report, indent=2))
    logger.info("report_path=%s", report["report_path"])


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
