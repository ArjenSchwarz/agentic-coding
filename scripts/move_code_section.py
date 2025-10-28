#!/usr/bin/env python3
"""
Script to move code sections between files.
Usage: python move_code_section.py <source_file> <start_line> <end_line> <dest_file> [--create-if-missing]
"""

import sys
import os
from pathlib import Path

def move_code_section(source_file, start_line, end_line, dest_file, create_if_missing=False):
    """Move a section of code from source_file to dest_file"""
    
    # Convert to 0-based indexing
    start_idx = start_line - 1
    end_idx = end_line - 1
    
    # Read source file
    try:
        with open(source_file, 'r') as f:
            source_lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: Source file {source_file} not found")
        return False
    
    # Validate line numbers
    if start_idx < 0 or end_idx >= len(source_lines) or start_idx > end_idx:
        print(f"Error: Invalid line range {start_line}-{end_line} for file with {len(source_lines)} lines")
        return False
    
    # Extract the section to move
    section_to_move = source_lines[start_idx:end_idx + 1]
    
    # Remove the section from source
    remaining_source = source_lines[:start_idx] + source_lines[end_idx + 1:]
    
    # Handle destination file
    dest_exists = os.path.exists(dest_file)
    
    if dest_exists:
        # Append to existing file
        with open(dest_file, 'r') as f:
            dest_lines = f.readlines()
        
        # Add the section at the end
        dest_lines.extend(section_to_move)
        
        with open(dest_file, 'w') as f:
            f.writelines(dest_lines)
    else:
        if create_if_missing:
            # Create new file with Go package header
            # Extract package name from source file
            package_name = "config"  # default
            for line in remaining_source:
                if line.strip().startswith("package "):
                    package_name = line.strip().split()[1]
                    break
            
            package_line = f"package {package_name}\n\n"
            
            # Find imports from source file
            imports_start = -1
            imports_end = -1
            for i, line in enumerate(remaining_source):
                if line.strip().startswith("import"):
                    imports_start = i
                    if line.strip().endswith(")"):
                        imports_end = i
                        break
                elif imports_start >= 0 and line.strip().endswith(")"):
                    imports_end = i
                    break
            
            imports_section = []
            if imports_start >= 0 and imports_end >= 0:
                imports_section = remaining_source[imports_start:imports_end + 1]
                imports_section.append("\n")
            
            with open(dest_file, 'w') as f:
                f.write(package_line)
                if imports_section:
                    f.writelines(imports_section)
                f.writelines(section_to_move)
        else:
            print(f"Error: Destination file {dest_file} does not exist. Use --create-if-missing to create it.")
            return False
    
    # Write back the modified source file
    with open(source_file, 'w') as f:
        f.writelines(remaining_source)
    
    print(f"Successfully moved lines {start_line}-{end_line} from {source_file} to {dest_file}")
    return True

def main():
    if len(sys.argv) < 5:
        print("Usage: python move_code_section.py <source_file> <start_line> <end_line> <dest_file> [--create-if-missing]")
        sys.exit(1)
    
    source_file = sys.argv[1]
    start_line = int(sys.argv[2])
    end_line = int(sys.argv[3])
    dest_file = sys.argv[4]
    create_if_missing = "--create-if-missing" in sys.argv[5:]
    
    success = move_code_section(source_file, start_line, end_line, dest_file, create_if_missing)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()