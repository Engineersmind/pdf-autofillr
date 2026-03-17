"""
pytest configuration for the pdf-autofiller-mapper SDK test suite.

Adds the sdk root (modules/mapper/sdk/) to sys.path so that
`import pdf_autofiller_mapper` works without installing the package first.
"""

import sys
import os

# Ensure modules/mapper/sdk/ is on the path when pytest is run from any directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
