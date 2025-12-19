"""
Script để import các phòng ban từ hardcoded mapping vào database
"""
import sqlite3

# Mapping từ code (hardcoded)
DEPARTMENT_MAPPINGS = {
    'BUD A': 'Bud_TimeSheet',
    'BUD B': 'Bud_TimeSheet',
    'BUD C': 'Bud_TimeSheet',
    'CREEK&RIVER': 'Creek&River_timesheet',
    'KIRI': 'KIRI TIME SHEET',
    'OFFICE': 'BACKOFFICE_TIMESHEET',
    'YORK': 'Chirashi_TimeSheet',
    'COMO': 'Chirashi_TimeSheet',
    'IT': 'IT_TimeSheet',
    'SCOPE': 'SCOPE_TimeSheet'
}

def import_departments():
    conn = sqlite3.connect('instance/attendance.db')
    cursor = conn.cursor()
    
    imported = 0
    updated = 0
    
    print('=' * 70)
    print('IMPORT PHÒNG BAN VÀO DATABASE')
    print('=' * 70)
    
    for dept_name, timesheet_file in DEPARTMENT_MAPPINGS.items():
        # Kiểm tra xem phòng ban đã tồn tại chưa
        cursor.execute('SELECT id, timesheet_file FROM departments WHERE name = ?', (dept_name,))
        existing = cursor.fetchone()
        
        if existing:
            # Nếu đã tồn tại nhưng chưa có timesheet_file, cập nhật
            if not existing[1]:
                cursor.execute('''
                    UPDATE departments 
                    SET timesheet_file = ?, updated_at = datetime('now')
                    WHERE id = ?
                ''', (timesheet_file, existing[0]))
                updated += 1
                print(f'✓ Cập nhật: {dept_name} -> {timesheet_file}')
            else:
                print(f'○ Đã có: {dept_name} -> {existing[1]}')
        else:
            # Thêm mới - tạo code từ tên (lấy 10 ký tự đầu)
            dept_code = dept_name[:10].upper().replace(' ', '_')
            cursor.execute('''
                INSERT INTO departments (name, code, timesheet_file, is_active, created_at, updated_at)
                VALUES (?, ?, ?, 1, datetime('now'), datetime('now'))
            ''', (dept_name, dept_code, timesheet_file))
            imported += 1
            print(f'✓ Thêm mới: {dept_name} -> {timesheet_file}')
    
    conn.commit()
    conn.close()
    
    print('=' * 70)
    print(f'Hoàn thành! Đã thêm {imported} phòng ban, cập nhật {updated} phòng ban')
    print('=' * 70)

if __name__ == '__main__':
    import_departments()

