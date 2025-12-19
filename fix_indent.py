#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fix indent issues in HTML files by removing double carriage returns"""

import os

def fix_file(filepath):
    """Fix double carriage returns in a file"""
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        
        # Fix \r\r\n -> \r\n
        fixed_content = content.replace(b'\r\r\n', b'\r\n')
        
        if content != fixed_content:
            with open(filepath, 'wb') as f:
                f.write(fixed_content)
            print(f"Fixed: {filepath}")
            return True
        else:
            print(f"No issues: {filepath}")
            return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

if __name__ == '__main__':
    # Fix the specific file
    fix_file('templates/admin/deleted_users.html')
    print("Done!")
