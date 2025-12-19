# -*- coding: utf-8 -*-
filepath = r'c:\Users\ADMIN\Desktop\231020253\attendances-management-system-dmi\templates\admin\deleted_users.html'

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix lines 734-735: need to add 4 more spaces (currently have 16, need 20)
for i in [733, 734]:  # 0-indexed for lines 734-735
    if i < len(lines):
        line = lines[i]
        # If line starts with exactly 16 spaces but not 20, add 4 more
        if line.startswith('                ') and not line.startswith('                    '):
            lines[i] = '    ' + line

# Fix line 747: closing }); should have 12 spaces, currently has 16
i = 746  # 0-indexed for line 747
if i < len(lines):
    line = lines[i]
    if line.strip() == '});' and line.startswith('                '):
        lines[i] = '            });\r\n'

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Done!')
