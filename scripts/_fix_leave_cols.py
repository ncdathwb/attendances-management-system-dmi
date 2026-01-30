import os, sqlite3

dbs = [
    r"C:\\Users\\Thinkpad\\Desktop\\THNG10~1\\attendances-management-system-dmi\\attendance.db",
    r"C:\\Users\\Thinkpad\\Desktop\\THNG10~1\\attendances-management-system-dmi\\instance\\attendance.db",
]

new_cols = {
    "step": "TEXT DEFAULT 'leader'",
    "current_approver_id": "INTEGER",
    "reject_reason": "TEXT",
    "team_leader_signature": "TEXT",
    "team_leader_signer_id": "INTEGER",
    "team_leader_approved_at": "TEXT",
    "manager_signature": "TEXT",
    "manager_signer_id": "INTEGER",
    "manager_approved_at": "TEXT",
    "admin_signature": "TEXT",
    "admin_signer_id": "INTEGER",
    "admin_approved_at": "TEXT",
}

# Security: Whitelist validation để prevent SQL injection
ALLOWED_COLUMNS = {
    'step', 'current_approver_id', 'reject_reason',
    'team_leader_signature', 'team_leader_signer_id', 'team_leader_approved_at',
    'manager_signature', 'manager_signer_id', 'manager_approved_at',
    'admin_signature', 'admin_signer_id', 'admin_approved_at'
}

ALLOWED_TYPES = {'TEXT', 'INTEGER', 'VARCHAR', 'DATETIME', 'BOOLEAN', 'DEFAULT'}

for db in dbs:
    print(f"[DB] {db}")
    if not os.path.exists(db):
        print("  - SKIP (not found)")
        continue
    con = sqlite3.connect(db)
    cur = con.cursor()
    t = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='leave_requests'").fetchone()
    if not t:
        print("  - WARN: table leave_requests not found")
        con.close()
        continue
    existing = {r[1] for r in cur.execute("PRAGMA table_info(leave_requests)").fetchall()}
    added = []
    for name, ddl in new_cols.items():
        if name not in existing:
            # Validate column name (whitelist)
            if name not in ALLOWED_COLUMNS:
                print(f"  - SKIP unsafe column: {name}")
                continue
            
            # Validate column type (extract first word)
            col_type_parts = ddl.split()
            if not col_type_parts:
                print(f"  - SKIP empty definition: {name}")
                continue
                
            col_type = col_type_parts[0].upper()
            if col_type not in ALLOWED_TYPES:
                print(f"  - SKIP unsafe type '{col_type}': {name}")
                continue
            
            try:
                cur.execute(f"ALTER TABLE leave_requests ADD COLUMN {name} {ddl}")
                added.append(name)
            except Exception as e:
                print(f"  - ERR add {name}: {e}")
    con.commit()
    cols_after = [r[1] for r in cur.execute("PRAGMA table_info(leave_requests)").fetchall()]
    con.close()
    print("  - ADDED:", added if added else "no-op")
    print("  - COLS :", ", ".join(cols_after))
