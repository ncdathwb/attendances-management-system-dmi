"""
Utility functions for processing leave data for Excel export
Xử lý dữ liệu nghỉ phép cho việc xuất Excel với tách từng ngày riêng biệt
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import sys


def _build_allocation_entries(available_types: List[Dict]) -> List[Dict]:
    """
    Tạo danh sách phân bổ loại nghỉ theo đúng thứ tự cố định và theo số ngày trong DB.
    Thứ tự: Phép năm -> Nghỉ không lương -> Nghỉ đặc biệt.
    Mỗi phần tử đại diện cho 1 dòng/ngày, với trường 'days' có thể là 1.0 hoặc phần lẻ.
    """
    if not available_types:
        return []

    # Bảo đảm thứ tự: annual -> unpaid -> special
    priority_order = {"annual": 0, "unpaid": 1, "special": 2}
    ordered = sorted(available_types, key=lambda t: priority_order.get(t["type"], 99))

    whole_entries: List[Dict] = []
    fractional_entries: List[Dict] = []
    for leave_type in ordered:
        total = float(leave_type["total_days"])
        whole_days = int(total)
        fractional = round(total - whole_days, 2)

        # Thêm các ngày nguyên trước (1.0 ngày)
        for _ in range(whole_days):
            whole_entries.append({
                "type": leave_type["type"],
                "name": leave_type["name"],
                "days": 1.0,
                "special_type": leave_type.get("special_type")
            })
        
        # Phần lẻ (0.5, 1.5, ...) sẽ được gom lại đưa xuống cuối danh sách
        if fractional > 0:
            fractional_entries.append({
                "type": leave_type["type"],
                "name": leave_type["name"],
                "days": fractional,
                "special_type": leave_type.get("special_type")
            })
    
    # Ưu tiên phân bổ đủ 1 ngày cho các dòng đầu tiên, sau đó mới đến các phần lẻ
    allocation: List[Dict] = whole_entries + fractional_entries
    return allocation


def split_leave_by_days(leave_request) -> List[Dict]:
    """
    Tách một đơn nghỉ phép thành các ngày riêng biệt
    
    Args:
        leave_request: LeaveRequest object
        
    Returns:
        List of dictionaries, mỗi dict chứa thông tin của một ngày nghỉ
    """
    start_date = leave_request.get_leave_from_datetime()
    end_date = leave_request.get_leave_to_datetime()
    
    # Tính số ngày nghỉ
    total_days = (end_date - start_date).days + 1
    
    # Lấy thông tin loại nghỉ có sẵn và tạo phân bổ xác định
    available_leave_types = get_available_leave_types(leave_request)
    allocation_entries = _build_allocation_entries(available_leave_types)
    
    # Tách thành từng ngày
    daily_leaves = []
    current_date = start_date.date()
    
    for day_index in range(total_days):
        # Tạo thông tin cho ngày hiện tại
        day_info = {
            'employee_name': leave_request.employee_name,
            'employee_code': leave_request.employee_code,
            'team': leave_request.team,
            'date': current_date,
            'start_time': start_date.time() if day_index == 0 else datetime.strptime("07:30", "%H:%M").time(),
            'end_time': end_date.time() if day_index == total_days - 1 else datetime.strptime("16:30", "%H:%M").time(),
            'reason': leave_request.get_reason_text(),
            'substitute_name': leave_request.substitute_name,
            'substitute_employee_id': leave_request.substitute_employee_id,
            'created_at': leave_request.created_at,
            'is_first_day': day_index == 0,
            'is_last_day': day_index == total_days - 1,
            'day_index': day_index,
            'total_days': total_days
        }
        
        # Xác định loại nghỉ cho ngày này theo phân bổ xác định từ DB
        if day_index < len(allocation_entries):
            allocated = allocation_entries[day_index]
        else:
            # Fallback: nếu số ngày lịch vượt quá tổng phân bổ, dùng loại đầu tiên
            allocated = allocation_entries[0] if allocation_entries else {
                'type': 'unknown', 'name': 'Không xác định', 'days': 1.0
            }

        day_info['leave_type'] = {
            'type': allocated['type'],
            'name': allocated['name'],
            'days': allocated.get('days', 1.0),
            'special_type': allocated.get('special_type')
        }
        
        daily_leaves.append(day_info)
        current_date += timedelta(days=1)
    
    return daily_leaves


def get_available_leave_types(leave_request) -> List[Dict]:
    """
    Lấy danh sách các loại nghỉ có sẵn từ đơn nghỉ phép
    
    Args:
        leave_request: LeaveRequest object
        
    Returns:
        List of dictionaries chứa thông tin loại nghỉ
    """
    available_types = []
    
    if leave_request.annual_leave_days > 0:
        available_types.append({
            'type': 'annual',
            'name': 'Phép năm',
            'total_days': leave_request.annual_leave_days
        })
    
    if leave_request.unpaid_leave_days > 0:
        available_types.append({
            'type': 'unpaid',
            'name': 'Nghỉ không lương',
            'total_days': leave_request.unpaid_leave_days
        })
    
    if leave_request.special_leave_days > 0:
        available_types.append({
            'type': 'special',
            'name': 'Nghỉ đặc biệt',
            'total_days': leave_request.special_leave_days,
            'special_type': leave_request.special_leave_type
        })
    
    return available_types


def determine_leave_type_for_day(leave_request, day_index: int, total_days: int, available_types: List[Dict]) -> Dict:
    """Giữ lại hàm cho tương thích nhưng trả về theo phân bổ xác định, không random."""
    allocation = _build_allocation_entries(available_types)
    if not allocation:
        return {'type': 'unknown', 'name': 'Không xác định', 'days': 1.0}
    chosen = allocation[day_index] if day_index < len(allocation) else allocation[0]
    return {
        'type': chosen['type'],
        'name': chosen['name'],
        'days': 1.0,
        'special_type': chosen.get('special_type')
    }


def handle_fractional_leave_days(leave_request) -> List[Dict]:
    """
    Xử lý các trường hợp nghỉ lẻ (0.5, 1.5, 2.5 ngày)
    
    Args:
        leave_request: LeaveRequest object
        
    Returns:
        List of dictionaries chứa thông tin nghỉ đã được xử lý
    """
    # Lấy thông tin loại nghỉ
    available_types = get_available_leave_types(leave_request)
    
    # Tính tổng số ngày nghỉ (bao gồm cả lẻ)
    total_leave_days = sum(lt['total_days'] for lt in available_types)
    
    # Nếu không có ngày lẻ, xử lý bình thường
    if total_leave_days == int(total_leave_days):
        return split_leave_by_days(leave_request)
    
    # Xử lý ngày lẻ
    start_date = leave_request.get_leave_from_datetime()
    end_date = leave_request.get_leave_to_datetime()
    
    # Tạo danh sách phân bổ theo tỷ lệ (xác định, không random)
    daily_leaves = []
    current_date = start_date.date()
    leave_allocation = _build_allocation_entries(available_types)
    
    # Tạo dữ liệu cho từng ngày
    for day_index, leave_type in enumerate(leave_allocation):
        # Xác định số ngày nghỉ cho ngày này
        days_for_this_day = leave_type['days'] if 'days' in leave_type else leave_type['total_days']
        
        # Tạo thông tin ngày
        day_info = {
            'employee_name': leave_request.employee_name,
            'employee_code': leave_request.employee_code,
            'team': leave_request.team,
            'date': current_date,
            'start_time': start_date.time() if day_index == 0 else datetime.strptime("07:30", "%H:%M").time(),
            'end_time': end_date.time() if day_index == len(leave_allocation) - 1 else datetime.strptime("16:30", "%H:%M").time(),
            'reason': leave_request.get_reason_text(),
            'substitute_name': leave_request.substitute_name,
            'substitute_employee_id': leave_request.substitute_employee_id,
            'created_at': leave_request.created_at,
            'is_first_day': day_index == 0,
            'is_last_day': day_index == len(leave_allocation) - 1,
            'day_index': day_index,
            'total_days': len(leave_allocation),
            'fractional_days': days_for_this_day
        }
        
        # Xác định loại nghỉ
        day_info['leave_type'] = {
            'type': leave_type['type'],
            'name': leave_type['name'],
            'days': days_for_this_day,
            'special_type': leave_type.get('special_type')
        }
        
        daily_leaves.append(day_info)
        current_date += timedelta(days=1)
    
    return daily_leaves


def determine_leave_type_for_fractional_day(leave_request, day_index: int, total_days: int, 
                                          available_types: List[Dict], days_for_this_day: float) -> Dict:
    """
    Xác định loại nghỉ cho ngày có số ngày lẻ
    
    Args:
        leave_request: LeaveRequest object
        day_index: Chỉ số ngày (0-based)
        total_days: Tổng số ngày nghỉ
        available_types: Danh sách loại nghỉ có sẵn
        days_for_this_day: Số ngày nghỉ cho ngày này (có thể lẻ)
        
    Returns:
        Dictionary chứa thông tin loại nghỉ cho ngày này
    """
    if not available_types:
        return {
            'type': 'unknown',
            'name': 'Không xác định',
            'days': days_for_this_day
        }
    
    # Nếu chỉ có 1 loại nghỉ, dùng loại đó
    if len(available_types) == 1:
        leave_type = available_types[0]
        return {
            'type': leave_type['type'],
            'name': leave_type['name'],
            'days': days_for_this_day,
            'special_type': leave_type.get('special_type')
        }
    
    # Nếu có nhiều loại nghỉ, random chọn
    weighted_types = []
    for leave_type in available_types:
        weight = int(leave_type['total_days'] * 10)
        weighted_types.extend([leave_type] * weight)
    
    # Không còn dùng random; chọn theo phân bổ xác định để khớp DB
    selected_type = weighted_types[0]
    
    return {
        'type': selected_type['type'],
        'name': selected_type['name'],
        'days': days_for_this_day,
        'special_type': selected_type.get('special_type')
    }


def process_leave_requests_for_excel(leave_requests) -> List[Dict]:
    """
    Xử lý tất cả đơn nghỉ phép để xuất Excel
    
    Args:
        leave_requests: List of LeaveRequest objects
        
    Returns:
        List of dictionaries, mỗi dict là một dòng trong Excel
    """
    all_daily_leaves = []
    
    for request in leave_requests:
        try:
            # Kiểm tra xem có ngày lẻ không
            available_types = get_available_leave_types(request)
            total_leave_days = sum(lt['total_days'] for lt in available_types)
            
            # Kiểm tra ngày lẻ chính xác hơn
            has_fractional = any(
                lt['total_days'] % 1 != 0 for lt in available_types
            )
            
            if has_fractional:
                # Có ngày lẻ, xử lý đặc biệt
                try:
                    print(f"[DEBUG] Processing fractional leave for {request.employee_name}: {total_leave_days} days", flush=True, file=sys.stderr)
                except Exception:
                    pass
                daily_leaves = handle_fractional_leave_days(request)
            else:
                # Không có ngày lẻ, xử lý bình thường
                daily_leaves = split_leave_by_days(request)
            
            all_daily_leaves.extend(daily_leaves)
            
        except Exception as e:
            try:
                print(f"[ERROR] Error processing leave request {request.id}: {e}", flush=True, file=sys.stderr)
            except Exception:
                pass
            # Thêm dữ liệu cơ bản nếu có lỗi
            try:
                from_date = request.get_leave_from_datetime().date()
                from_time = request.get_leave_from_datetime().time()
                to_time = request.get_leave_to_datetime().time()
            except Exception:
                # Nếu không lấy được ngày giờ, dùng giá trị mặc định
                from_date = datetime.now().date()
                from_time = datetime.strptime("07:30", "%H:%M").time()
                to_time = datetime.strptime("16:30", "%H:%M").time()
            
            try:
                all_daily_leaves.append({
                    'employee_name': getattr(request, 'employee_name', 'Unknown'),
                    'employee_code': getattr(request, 'employee_code', ''),
                    'team': getattr(request, 'team', 'Unknown'),
                    'date': from_date,
                    'start_time': from_time,
                    'end_time': to_time,
                    'reason': getattr(request, 'get_reason_text', lambda: '')() if hasattr(request, 'get_reason_text') else '',
                    'substitute_name': getattr(request, 'substitute_name', ''),
                    'substitute_employee_id': getattr(request, 'substitute_employee_id', None),
                    'created_at': getattr(request, 'created_at', datetime.now()),
                    'leave_type': {
                        'type': 'unknown',
                        'name': 'Lỗi xử lý',
                        'days': 1.0
                    },
                    'fractional_days': 1.0
                })
            except Exception as fallback_err:
                try:
                    print(f"[ERROR] Error creating fallback data for request {request.id}: {fallback_err}", flush=True, file=sys.stderr)
                except Exception:
                    pass
    
    return all_daily_leaves
