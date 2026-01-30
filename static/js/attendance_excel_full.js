document.addEventListener('DOMContentLoaded', function () {
    const btnExportFull = document.getElementById('btnExportAttendanceExcelFull');
    if (btnExportFull) {
        btnExportFull.addEventListener('click', exportAttendanceExcelFull);
    }
});



function exportAttendanceExcelFull() {
    // Show loading
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            title: 'Đang xử lý...',
            text: 'Vui lòng đợi trong giây lát',
            allowOutsideClick: false,
            showConfirmButton: false,
            willOpen: () => { Swal.showLoading(); }
        });
    }

    // Get filters from UI (if available)
    const params = new URLSearchParams();
    const searchName = document.getElementById('allHistorySearchName')?.value || '';
    const department = document.getElementById('allHistoryDepartment')?.value || '';
    const fromDate = document.getElementById('allHistoryDateFrom')?.value || '';
    const toDate = document.getElementById('allHistoryDateTo')?.value || '';
    const monthFrom = document.getElementById('allHistoryMonthFrom')?.value || '';
    const monthTo = document.getElementById('allHistoryMonthTo')?.value || '';
    const yearFrom = document.getElementById('allHistoryYearFrom')?.value || '';
    const yearTo = document.getElementById('allHistoryYearTo')?.value || '';

    if (searchName) params.append('q', searchName);
    if (department) params.append('department', department);
    if (fromDate) params.append('from_date', fromDate);
    if (toDate) params.append('to_date', toDate);
    if (monthFrom) params.append('month_from', monthFrom);
    if (monthTo) params.append('month_to', monthTo);
    if (yearFrom) params.append('year_from', yearFrom);
    if (yearTo) params.append('year_to', yearTo);

    // Use fetch to check response before downloading
    const url = '/export-attendance-excel-full?' + params.toString();

    fetch(url, {
        method: 'GET',
        credentials: 'same-origin' // Include cookies for session
    })
        .then(async response => {
            // Debug logging
            console.log('[Excel Export] Response URL:', response.url);
            console.log('[Excel Export] Response Status:', response.status);
            console.log('[Excel Export] Response OK:', response.ok);

            // Check if session expired (401 Unauthorized)
            if (response.status === 401) {
                console.error('[Excel Export] 401 Unauthorized - session expired');
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        title: 'Phiên làm việc đã hết hạn',
                        text: 'Vui lòng đăng nhập lại',
                        icon: 'warning',
                        confirmButtonText: 'Đăng nhập'
                    }).then(() => {
                        window.location.href = '/login';
                    });
                } else {
                    alert('Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại.');
                    window.location.href = '/login';
                }
                return null;
            }

            // Check if response is OK
            if (!response.ok) {
                console.error('[Excel Export] Response not OK:', response.status, response.statusText);

                // Try to parse JSON error response from backend
                let errorMessage = `Server error: ${response.status} ${response.statusText}`;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || errorData.message || errorMessage;
                    console.log('[Excel Export] Error message from server:', errorMessage);
                } catch (parseError) {
                    console.error('[Excel Export] Failed to parse error JSON, using generic message');
                }
                // Throw error OUTSIDE try-catch
                throw new Error(errorMessage);
            }

            // Check content type to ensure it's actually an Excel file
            const contentType = response.headers.get('Content-Type');
            console.log('[Excel Export] Content-Type:', contentType);

            // Check for HTML content (login page) - THIS is the primary check
            if (contentType && (contentType.includes('text/html') || contentType.includes('text/plain'))) {
                // Server returned HTML instead of Excel - likely session expired
                console.error('[Excel Export] Got HTML instead of Excel - session likely expired');
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        title: 'Phiên làm việc đã hết hạn',
                        text: 'Vui lòng đăng nhập lại',
                        icon: 'warning',
                        confirmButtonText: 'Đăng nhập'
                    }).then(() => {
                        window.location.href = '/login';
                    });
                } else {
                    alert('Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại.');
                    window.location.href = '/login';
                }
                return null;
            }

            // Verify it's actually an Excel file
            if (!contentType || !contentType.includes('spreadsheet')) {
                console.error('[Excel Export] Invalid content type:', contentType);
                throw new Error('Server không trả về file Excel. Vui lòng thử lại.');
            }

            console.log('[Excel Export] Valid Excel file detected, proceeding with download');
            // Valid Excel response
            return response.blob();
        })
        .then(blob => {
            if (!blob) return; // Session expired, already handled above

            // Create download link
            const downloadUrl = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = `cham_cong_full_${new Date().toISOString().slice(0, 10)}.xlsx`;
            link.style.display = 'none';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            // Clean up blob URL
            setTimeout(() => window.URL.revokeObjectURL(downloadUrl), 1000);

            // Show success message
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: 'Thành công!',
                    text: 'File Excel đã được tải xuống',
                    icon: 'success',
                    timer: 2000,
                    showConfirmButton: false
                });
            }
        })
        .catch(error => {
            console.error('Export error:', error);

            // Hiển thị toast error (thống nhất với các nút khác)
            if (typeof Swal !== 'undefined') {
                const Toast = Swal.mixin({
                    toast: true,
                    position: 'top-end',
                    showConfirmButton: false,
                    timer: 4000,
                    timerProgressBar: true,
                    didOpen: (toast) => {
                        toast.addEventListener('mouseenter', Swal.stopTimer);
                        toast.addEventListener('mouseleave', Swal.resumeTimer);
                    }
                });

                Toast.fire({
                    icon: 'error',
                    title: error.message || 'Không thể tải file Excel. Vui lòng thử lại.'
                });
            } else {
                alert('Lỗi: ' + (error.message || 'Không thể tải file Excel'));
            }
        });
}
