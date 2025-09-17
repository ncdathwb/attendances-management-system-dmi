#!/usr/bin/env python3
"""
Script để dọn dẹp debug prints và comments không cần thiết trong app.py
"""

import re
import os

def clean_debug_prints(file_path):
    """Xóa tất cả debug prints và comments không cần thiết"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Backup original file
    backup_path = file_path + '.backup'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    lines = content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Skip debug print lines
        if re.search(r'print\s*\(\s*["\']?DEBUG', line, re.IGNORECASE):
            continue
        if re.search(r'print\s*\(\s*f["\'].*DEBUG', line, re.IGNORECASE):
            continue
        if re.search(r'print\s*\(\s*["\'].*debug.*["\']', line, re.IGNORECASE):
            continue
        
        # Skip standalone comment lines that are not important
        stripped = line.strip()
        if stripped.startswith('#') and not any(keyword in stripped.lower() for keyword in [
            'important', 'note', 'todo', 'fixme', 'hack', 'warning', 'caution'
        ]):
            # Keep only important comments
            if not any(important in stripped.lower() for important in [
                'csrf', 'security', 'validation', 'authentication', 'authorization',
                'database', 'migration', 'config', 'environment', 'production'
            ]):
                continue
        
        # Remove inline debug comments
        line = re.sub(r'\s*#\s*debug.*$', '', line, flags=re.IGNORECASE)
        line = re.sub(r'\s*#\s*thêm log.*$', '', line, flags=re.IGNORECASE)
        
        cleaned_lines.append(line)
    
    # Remove excessive empty lines
    final_lines = []
    prev_empty = False
    
    for line in cleaned_lines:
        is_empty = line.strip() == ''
        if is_empty and prev_empty:
            continue
        final_lines.append(line)
        prev_empty = is_empty
    
    # Write cleaned content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(final_lines))
    
    print(f"Cleaned {file_path}")
    print(f"Original lines: {len(lines)}")
    print(f"Cleaned lines: {len(final_lines)}")
    print(f"Removed lines: {len(lines) - len(final_lines)}")

if __name__ == "__main__":
    # Clean app.py
    if os.path.exists('app.py'):
        clean_debug_prints('app.py')
    else:
        print("app.py not found")
