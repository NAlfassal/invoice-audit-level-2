"""Entry point so `python -m audit <stage>` works."""

import sys

from audit.cli import main

sys.exit(main())
