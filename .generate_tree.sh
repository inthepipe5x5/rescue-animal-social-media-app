#!/bin/bash

# Name of the output file
output_file="project_structure.txt"

# Check if tree command is installed
if ! command -v tree &> /dev/null
then
    echo "tree command could not be found. Please install it first."
    exit 1
fi

# Run tree command, excluding venv, __pycache__, and .git directories
# Use sed to remove color codes
tree -L 3 -I 'venv|__pycache__|.git' --charset=ascii | sed -r "s/\x1B\[([0-9]{1,3}(;[0-9]{1,2})?)?[mGK]//g" > "$output_file"

echo "Project structure has been saved to $output_file"
