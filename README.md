# Attendance Management System - DMI

A comprehensive attendance management system built with Flask for DMI company. This system allows employees to record their attendance, managers to approve records, and administrators to manage the entire system.

## Features

### For Employees
- Record daily attendance (check-in/check-out times)
- View attendance history
- Submit leave requests
- Edit attendance records before approval
- View approval status

### For Team Leaders
- Approve attendance records for team members
- View team attendance history
- Manage team members

### For Managers
- Approve attendance records after team leader approval
- View department-wide attendance
- Manage department members

### For Administrators
- Full system access
- User management
- View all attendance records
- System configuration

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: HTML, CSS, JavaScript
- **Authentication**: Flask-Login
- **Database Migrations**: Flask-Migrate

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ncdathwb/attendance-management-system-dmi.git
   cd attendance-management-system-dmi
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize the database**
   ```bash
   python init_db.py
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the application**
   Open your browser and go to `http://localhost:5000`

## Database Setup

The system comes with a pre-configured user list in `danhsach.txt`. To initialize the database with these users:

```bash
python init_db.py
```

### Default Admin Account
- **Employee ID**: 1395
- **Password**: dat123
- **Role**: ADMIN

## Usage

### Login
- Use your employee ID and password to log in
- The system supports role-based access control

### Recording Attendance
1. Select the date
2. Choose the day type (normal, weekend, holiday)
3. Enter check-in and check-out times
4. Add break time and notes if needed
5. Submit the record

### Approval Process
1. **Team Leader** approves initial records
2. **Manager** reviews team leader approvals
3. **Administrator** gives final approval

## File Structure

```
DMI-CHAMCONG/
├── app.py                 # Main Flask application
├── init_db.py            # Database initialization script
├── fake_attendance_data.py # Script to generate test data
├── requirements.txt      # Python dependencies
├── danhsach.txt         # User list for initialization
├── static/              # Static files (CSS, JS)
├── templates/           # HTML templates
└── migrations/          # Database migration files
```

## API Endpoints

### Authentication
- `POST /login` - User login
- `GET /logout` - User logout

### Attendance
- `POST /api/attendance` - Record new attendance
- `GET /api/attendance/history` - Get attendance history
- `PUT /api/attendance/<id>` - Update attendance record
- `DELETE /api/attendance/<id>` - Delete attendance record
- `POST /api/attendance/<id>/approve` - Approve/reject attendance

### User Management
- `POST /switch-role` - Switch user role
- `GET /admin/users` - Admin user management

## Configuration

The application uses the following configuration:

- **Database**: SQLite (`attendance.db`)
- **Secret Key**: Configured in `app.py`
- **Session Management**: Flask session

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is proprietary software for DMI company.

## Support

For support and questions, please contact the development team. 