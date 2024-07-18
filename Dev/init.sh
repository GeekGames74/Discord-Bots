#!/bin/bash

# Get the directory of current file
FILE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

# Set the PYTHONPATH environment variable
export PYTHONPATH="$PARENT_DIR"
echo "PYTHONPATH is set to $PYTHONPATH"
