# Direct endpoint for save-credentials that matches client expectations
import sys
import os

# Add the parent directory to path to import working_mcp
current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from working_mcp import handler

# Use the same handler for consistency
