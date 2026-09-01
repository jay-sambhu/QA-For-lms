import os
import sys

# Ensure repository root is always in sys.path for test discovery and modular imports
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
