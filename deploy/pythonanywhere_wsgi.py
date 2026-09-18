"""WSGI entry for PythonAnywhere. Paste this into the file linked from the Web tab
("WSGI configuration file"), replacing everything in it.

Adjust HOME if your PythonAnywhere username isn't ethanmiclat.
"""

import os
import sys

HOME = "/home/ethanmiclat"
REPO = f"{HOME}/financialplanner"

# A public portfolio link: every visitor gets a private sandbox, and the owner's
# real profile is never read.
os.environ["FP_DEMO"] = "1"
os.environ["FP_DEMO_DIR"] = f"{HOME}/footing-demo"
# Only the GitHub Pages site may call the API from a browser.
os.environ["FP_CORS_ORIGINS"] = "https://ethanmiclat.github.io"

sys.path.insert(0, f"{REPO}/backend")

from app import app as application  # noqa: E402
