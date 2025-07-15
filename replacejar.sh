#!/bin/bash

# Usage: ./update_file_in_all_dirs.sh <filename> <search_directory>

# Check for valid input
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <filename> <search_directory>"
    exit 1
fi

FILENAME="$1"
SEARCH_DIR="$2"
SOURCE_FILE="./$FILENAME"

# Validate source file
if [ ! -f "$SOURCE_FILE" ]; then
    echo "Error: File '$FILENAME' not found in current directory ($PWD)"
    exit 2
fi

# Find all occurrences of the file
FOUND_PATHS=$(find "$SEARCH_DIR" -type f -name "$FILENAME")

if [ -z "$FOUND_PATHS" ]; then
    echo "No files named '$FILENAME' found in $SEARCH_DIR"
    exit 0
fi

# Copy the updated file to all found locations
echo "Copying updated '$FILENAME' to:"
while IFS= read -r FILE_PATH; do
    DIR_PATH=$(dirname "$FILE_PATH")
    cp "$SOURCE_FILE" "$DIR_PATH/"
    echo " - $DIR_PATH/"
done <<< "$FOUND_PATHS"

echo "✅ Done."

