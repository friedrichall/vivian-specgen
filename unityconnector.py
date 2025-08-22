#!/usr/bin/env python3
"""Print selected interaction elements and description.

This script no longer writes specification files. The Unity editor window
passes a natural language description followed by the names of selected
interaction elements as command line arguments. The values are exposed as
top-level variables and printed for downstream processing.
"""

import sys


description = sys.argv[1] if len(sys.argv) > 1 else ""
args = sys.argv[2:]
object_interactions = {
    args[i]: args[i + 1] for i in range(0, len(args), 2)
}

print("Unity Connector:\n______________________________\n")
print("description:", description)
for name, element in object_interactions.items():
    print(f"{name}: {element}")

