"""
User seeding data for the attendance management system
"""
import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, User
from werkzeug.security import generate_password_hash
import random

# Fix Unicode output for Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def seed_users():
    """Seed users table with initial data"""
    
    departments = [
        'BUD A', 'BUD B', 'BUD C', 'SCOPE', 'KIRI', 'CREEK&RIVER', 'COMO', 'OFFICE', 'YORK'
    ]
    
    # Vietnamese name components
    ho_list = [
        'Nguyễn', 'Trần', 'Lê', 'Phạm', 'Hoàng', 'Phan', 'Vũ', 'Đặng', 
        'Bùi', 'Đỗ', 'Hồ', 'Ngô', 'Dương', 'Lý'
    ]
    tendem_list = [
        'Văn', 'Thị', 'Hữu', 'Đức', 'Minh', 'Thanh', 'Xuân', 'Quang', 
        'Ngọc', 'Trọng', 'Phước', 'Gia', 'Tuấn', 'Thành', 'Công', 'Thái', 
        'Anh', 'Kim', 'Quốc', 'Thảo', 'Hải', 'Khánh', 'Chí', 'Tiến', 
        'Thúy', 'Thu', 'Lan', 'Mai', 'Hà', 'Hương', 'Tú'
    ]
    ten_list = [
        'An', 'Bình', 'Châu', 'Dũng', 'Duy', 'Giang', 'Hà', 'Hải', 
        'Hạnh', 'Hiếu', 'Hoa', 'Hòa', 'Hùng', 'Khánh', 'Lan', 'Linh', 
        'Loan', 'Long', 'Mai', 'Minh', 'Nam', 'Nga', 'Ngân', 'Ngọc', 
        'Nhung', 'Phát', 'Phú', 'Phúc', 'Quang', 'Quân', 'Quyên', 'Sơn', 
        'Tâm', 'Tân', 'Thảo', 'Thành', 'Thắng', 'Thảo', 'Thịnh', 'Thu', 
        'Thủy', 'Trang', 'Trí', 'Trinh', 'Trung', 'Tú', 'Tuấn', 'Tuyết', 
        'Vân', 'Việt', 'Yến'
    ]
    
    def generate_vietnamese_name():
        """Generate a random Vietnamese name"""
        ho = random.choice(ho_list)
        tendem = random.choice(tendem_list)
        ten = random.choice(ten_list)
        return f"{ho} {tendem} {ten}"
    
    def generate_email(name, employee_id):
        """Generate email from name and employee ID"""
        # Remove diacritics and convert to lowercase
        name_parts = name.lower().split()
        # Use the last name (ten) for email
        last_name = name_parts[-1]
        # Remove Vietnamese diacritics
        diacritics_map = {
            'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
            'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
            'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
            'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
            'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
            'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
            'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
            'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
            'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
            'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
            'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
            'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
            'đ': 'd'
        }
        
        clean_name = ''
        for char in last_name:
            clean_name += diacritics_map.get(char, char)
        
        return f"{clean_name}{employee_id}@gmail.com"
    
    # Default admin user
    admin_user = {
        'name': 'Nguyễn Công Đạt',
        'employee_id': 1395,
        'password': '123456',
        'roles': 'EMPLOYEE,TEAM_LEADER,MANAGER,ADMIN',
        'department': 'OFFICE',
        'email': 'n-congdat@dmi-acraft.net'
    }
    
    users_data = [admin_user]
    employee_id_counter = 2000
    used_names = set()
    used_names.add(admin_user['name'])
    
    # Generate users for each department
    for dept in departments:
        dept_users = []
        
        # Generate 10 users per department
        for i in range(10):
            # Generate unique name
            while True:
                name = generate_vietnamese_name()
                if name not in used_names:
                    used_names.add(name)
                    break
            
            emp_id = employee_id_counter
            employee_id_counter += 1
            
            email = generate_email(name, emp_id)
            
            dept_users.append({
                'name': name,
                'employee_id': emp_id,
                'password': '123456',
                'roles': 'EMPLOYEE',
                'department': dept,
                'email': email
            })
        
        # Assign one team leader per department
        team_leader_idx = random.randint(0, 9)
        dept_users[team_leader_idx]['roles'] += ',TEAM_LEADER'
        
        users_data.extend(dept_users)
    
    # Insert users into database
    with app.app_context():
        for user_data in users_data:
            # Check if user already exists
            existing_user = User.query.filter_by(employee_id=user_data['employee_id']).first()
            if existing_user:
                # Nếu là admin thì cập nhật email
                if user_data['employee_id'] == 1395:
                    existing_user.email = user_data['email']
                    db.session.commit()
                    print(f"Updated email for admin: {user_data['email']}")
                else:
                    print(f"User {user_data['name']} (ID: {user_data['employee_id']}) already exists, skipping...")
                continue
            
            # Create new user
            user = User(
                name=user_data['name'],
                employee_id=user_data['employee_id'],
                roles=user_data['roles'],
                department=user_data['department'],
                email=user_data['email']
            )
            user.set_password(user_data['password'])
            
            db.session.add(user)
            print(f"Created user: {user_data['name']} (ID: {user_data['employee_id']}) - {user_data['department']} - {user_data['email']}")
        
        try:
            db.session.commit()
            print(f"\n✅ Successfully seeded {len(users_data)} users!")
            
            # Generate user list file
            generate_user_list_file(users_data)
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error seeding users: {e}")
            raise

def generate_user_list_file(users_data):
    """Generate a text file with user information"""
    with open('user_list.txt', 'w', encoding='utf-8') as f:
        f.write('Tên | Mã NV | Email | Mật khẩu | Phòng ban | Vai trò\n')
        f.write('-' * 100 + '\n')
        
        for user in users_data:
            f.write(f"{user['name']} | {user['employee_id']} | {user['email']} | {user['password']} | {user['department']} | {user['roles']}\n")
    
    print("📄 Generated user_list.txt file")

def clear_users():
    """Clear all users except admin"""
    with app.app_context():
        try:
            # Keep admin user
            admin_user = User.query.filter_by(employee_id=1395).first()
            if admin_user:
                deleted_count = User.query.filter(User.employee_id != 1395).delete()
                db.session.commit()
                print(f"✅ Deleted {deleted_count} users (admin user preserved)")
            else:
                deleted_count = User.query.delete()
                db.session.commit()
                print(f"✅ Deleted {deleted_count} users")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error clearing users: {e}")
            raise

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'seed':
            seed_users()
        elif command == 'clear':
            clear_users()
        else:
            print("Usage: python users.py [seed|clear]")
    else:
        print("Seeding users...")
        seed_users() 