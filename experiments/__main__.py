"""``python -m experiments`` entry point."""

from __future__ import annotations

import sys

from experiments.suite import main

if __name__ == "__main__":
    sys.exit(main())
