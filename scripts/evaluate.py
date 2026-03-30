"""
Evaluation entrypoint script.

Convenience wrapper to run the evaluation suite from the repo root.
"""

# Standard library
import runpy


if __name__ == "__main__":
    runpy.run_module("eval.evaluate", run_name="__main__")
