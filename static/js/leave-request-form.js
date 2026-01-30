        // Auto-fill current user info if not editing
        document.addEventListener('DOMContentLoaded', function () {
            // Force clear validation state on page load
            const timeInputs = ['leave_from_time', 'leave_to_time', 'leave_from_date', 'leave_to_date'];
            timeInputs.forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    el.classList.remove('is-invalid');
                }
            });

            // Hiển thị toast thông báo khi truy cập trang đăng ký nghỉ phép
            showToast('Chào mừng bạn đến với hệ thống đăng ký nghỉ phép.', 'success');

            // You can add logic here to auto-fill user info from session
            // For now, we'll leave it manual
            const halfStepFields = ['annual_leave_days', 'unpaid_leave_days', 'special_leave_days'];
            function isHalfStep(val) {
                const num = parseFloat(val);
                if (isNaN(num) || num < 0) return false;
                return Math.abs((num * 2) - Math.round(num * 2)) < 1e-9; // multiples of 0.5
            }
            halfStepFields.forEach(id => {
                const el = document.getElementById(id);
                if (!el) return;

                // Validation function
                function validateField() {
                    const v = el.value;
                    if (v === '') {
                        el.setCustomValidity('');
                        el.classList.remove('is-invalid');
                        return;
                    }
                    if (!isHalfStep(v)) {
                        el.setCustomValidity('Giá trị phải là bội số của 0.5 (0.5, 1.0, 1.5, ...)');
                        el.classList.add('is-invalid');
                    } else {
                        el.setCustomValidity('');
                        el.classList.remove('is-invalid');
                    }
                }

                // Validate chỉ khi blur để giảm thiểu spam
                el.addEventListener('blur', validateField);
            });

            // Hiển thị khung giờ theo ca chọn
            const shiftSelect = document.getElementById('leave_shift_code');
            const shiftWindow = document.getElementById('leave_shift_window');
            const shiftMap = {
                '1': '07:30 - 16:30',
                '2': '09:00 - 18:00',
                '3': '11:00 - 20:00',
                '4': '08:00 - 17:00'
            };
            if (shiftSelect && shiftWindow) {
                const applyShift = () => {
                    if (shiftSelect.value) {
                        shiftWindow.textContent = shiftMap[shiftSelect.value] || '08:00 - 17:00';
                        // Bỏ lỗi khi đã chọn ca
                        shiftSelect.classList.remove('is-invalid');
                    } else {
                        shiftWindow.textContent = '-- Chọn ca để xem khung giờ --';
                    }
                };
                shiftSelect.addEventListener('change', applyShift);
                applyShift();
            }

            // Tính tổng số ngày và hiển thị real-time
            const totalDaysDisplay = document.getElementById('total-days-display');
            const daysStatus = document.getElementById('days-status');
            const leaveFromDate = document.getElementById('leave_from_date');
            const leaveToDate = document.getElementById('leave_to_date');
            const leaveDaysInputs = ['annual_leave_days', 'unpaid_leave_days', 'special_leave_days'];
            const teamEl = document.getElementById('team');
            const scopeWrap = document.getElementById('scope-days-wrapper');
            const yorkWrap = document.getElementById('york-days-wrapper');
            let isDateTimeRangeInvalid = false; // trạng thái phạm vi ngày giờ

            function updateTotalDays() {
                const parseNum = (v) => parseFloat(v || '0') || 0;
                const total = leaveDaysInputs.reduce((sum, id) => {
                    return sum + parseNum(document.getElementById(id).value);
                }, 0);
                totalDaysDisplay.textContent = total;

                // Tính khoảng thời gian thực tế sử dụng phép
                if (leaveFromDate.value && leaveToDate.value &&
                    document.getElementById('leave_from_time').value &&
                    document.getElementById('leave_to_time').value) {
                    if (isDateTimeRangeInvalid) {
                        daysStatus.innerHTML = 'Chọn đầy đủ thông tin để xem giới hạn';
                        return;
                    }

                    const fromDate = new Date(leaveFromDate.value);
                    const toDate = new Date(leaveToDate.value);
                    let fromTime = document.getElementById('leave_from_time').value;
                    let toTime = document.getElementById('leave_to_time').value;
                    const shiftCode = document.getElementById('leave_shift_code').value;

                    // Normalize thời gian để xử lý đúng định dạng SA/CH/AM/PM
                    fromTime = normalizeTimeFormat(fromTime);
                    toTime = normalizeTimeFormat(toTime);

                    const actualLeaveDays = shiftCode ? calculateActualLeaveDays(fromDate, toDate, fromTime, toTime, shiftCode) : 0;

                    // Cập nhật trạng thái
                    if (total > actualLeaveDays) {
                        daysStatus.innerHTML = `<span class="text-danger"><strong>❌ VƯỢT QUÁ!</strong> Cần giảm xuống còn ${actualLeaveDays} ngày để gửi đơn</span>`;
                    } else if (total === actualLeaveDays) {
                        daysStatus.innerHTML = `<span class="text-success"><strong>✅ ĐÚNG RỒI!</strong> Đã xin đúng ${actualLeaveDays} ngày - có thể gửi đơn</span>`;
                    } else if (total > 0) {
                        daysStatus.innerHTML = `<span class="text-warning"><strong>⚠️ CHƯA ĐỦ!</strong> Cần thêm ${actualLeaveDays - total} ngày nữa để gửi đơn</span>`;
                    } else {
                        daysStatus.innerHTML = `<span class="text-info"><strong>ℹ️ HƯỚNG DẪN:</strong> Cần xin đúng ${actualLeaveDays} ngày để gửi đơn</span>`;
                    }

                    // Thêm thông tin số ngày cần thiết
                    const requiredDays = document.querySelector('.alert-info p:last-child');
                    if (requiredDays) {
                        requiredDays.innerHTML = `Khoảng thời gian thực tế: ${actualLeaveDays} ngày (tính theo ca ${shiftCode})`;
                    }
                } else {
                    daysStatus.innerHTML = 'Chọn đầy đủ thông tin để xem giới hạn';
                }
            }

            // Cập nhật khi thay đổi số ngày nghỉ
            leaveDaysInputs.forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    el.addEventListener('input', updateTotalDays);
                }
            });

            // Hàm đảm bảo khoảng ngày hợp lệ: Từ ngày <= Đến ngày
            function enforceDateRange(strict = false) {
                if (!leaveFromDate || !leaveToDate) return;
                // Đồng bộ min/max để hỗ trợ kiểm tra ngay trong UI
                if (leaveFromDate.value) {
                    leaveToDate.min = leaveFromDate.value;
                } else {
                    leaveToDate.removeAttribute('min');
                }
                if (leaveToDate.value) {
                    leaveFromDate.max = leaveToDate.value;
                } else {
                    leaveFromDate.removeAttribute('max');
                }
                // Chỉ kiểm tra logic nội bộ; không hiển thị dưới input
                const from = leaveFromDate.value ? new Date(leaveFromDate.value) : null;
                const to = leaveToDate.value ? new Date(leaveToDate.value) : null;
                if (from && to && from > to) {
                    // không set invalid UI tại đây
                    // when not strict, don't set errors while typing
                } else {
                    // không thao tác UI khi hợp lệ
                }
            }

            // Hàm kiểm tra đầy đủ ngày giờ: start < end (bao gồm cả thời gian)
            function validateDateTimeOnBlur() {
                const fromDateEl = document.getElementById('leave_from_date');
                const toDateEl = document.getElementById('leave_to_date');
                const fromTimeEl = document.getElementById('leave_from_time');
                const toTimeEl = document.getElementById('leave_to_time');
                if (!(fromDateEl && toDateEl && fromTimeEl && toTimeEl)) return;

                const fd = fromDateEl.value;
                const td = toDateEl.value;
                let ft = fromTimeEl.value || '00:00';
                let tt = toTimeEl.value || '00:00';

                if (!fd || !td) return; // thiếu giá trị thì bỏ qua

                // Xử lý định dạng thời gian có SA/CH
                ft = normalizeTimeFormat(ft);
                tt = normalizeTimeFormat(tt);

                const start = new Date(`${fd}T${ft}:00`);
                const end = new Date(`${td}T${tt}:00`);

                // Debug: Log thời gian để kiểm tra
                console.log('Validation Debug:', {
                    fromDate: fd,
                    toDate: td,
                    fromTime: ft,
                    toTime: tt,
                    start: start,
                    end: end,
                    startTime: start.getTime(),
                    endTime: end.getTime(),
                    isValid: start < end
                });

                if (!isNaN(start.getTime()) && !isNaN(end.getTime()) && start >= end) {
                    // Khoanh đỏ cả 4 input khi sai và chỉ báo qua toast
                    fromDateEl.classList.add('is-invalid');
                    toDateEl.classList.add('is-invalid');
                    fromTimeEl.classList.add('is-invalid');
                    toTimeEl.classList.add('is-invalid');
                    isDateTimeRangeInvalid = true;
                    try { showToast('Thời gian từ ngày giờ phải nhỏ hơn đến ngày giờ', 'error'); } catch (_) { }
                    updateTotalDays();
                } else {
                    // Kiểm tra thêm: Giờ kết thúc không được vượt quá giờ ra khỏi ca
                    const shiftCode = document.getElementById('leave_shift_code').value;
                    const shiftRanges = {
                        '1': { start: '07:30', end: '16:30' },
                        '2': { start: '09:00', end: '18:00' },
                        '3': { start: '11:00', end: '20:00' },
                        '4': { start: '08:00', end: '17:00' }
                    };

                    let isShiftTimeInvalid = false;
                    if (shiftCode in shiftRanges) { // Kiểm tra ngay cả khi chưa chọn ngày
                        const shiftStartTime = shiftRanges[shiftCode].start;
                        const shiftEndTime = shiftRanges[shiftCode].end;
                        const shiftStartMinutes = timeToMinutes(shiftStartTime);
                        const shiftEndMinutes = timeToMinutes(shiftEndTime);
                        const fromTimeMinutes = timeToMinutes(ft);
                        const toTimeMinutes = timeToMinutes(tt);

                        // Kiểm tra giờ bắt đầu không được trước giờ vào ca (chỉ khi có giờ bắt đầu)
                        if (ft && fromTimeMinutes < shiftStartMinutes) {
                            fromTimeEl.classList.add('is-invalid');
                            isShiftTimeInvalid = true;
                            try { showToast(`❌ Giờ bắt đầu: ${ft} → Lỗi "không được trước giờ vào ca (${shiftStartTime})"`, 'error'); } catch (_) { }
                        }

                        // Kiểm tra giờ kết thúc không được vượt quá giờ ra khỏi ca (chỉ khi có giờ kết thúc)
                        if (tt && toTimeMinutes > shiftEndMinutes) {
                            toTimeEl.classList.add('is-invalid');
                            isShiftTimeInvalid = true;
                            try { showToast(`❌ Giờ kết thúc: ${tt} → Lỗi "không được vượt quá giờ ra khỏi ca (${shiftEndTime})"`, 'error'); } catch (_) { }
                        }
                    }

                    if (!isShiftTimeInvalid) {
                        // Hợp lệ: bỏ khoanh đỏ và cho phép hiển thị tính toán
                        fromDateEl.classList.remove('is-invalid');
                        toDateEl.classList.remove('is-invalid');
                        fromTimeEl.classList.remove('is-invalid');
                        toTimeEl.classList.remove('is-invalid');
                        isDateTimeRangeInvalid = false;
                        updateTotalDays();
                    }
                }
            }

            // Hàm kiểm tra im lặng để gỡ border đỏ khi đã hợp lệ (không hiện toast)
            function validateDateTimeSilent() {
                const fromDateEl = document.getElementById('leave_from_date');
                const toDateEl = document.getElementById('leave_to_date');
                const fromTimeEl = document.getElementById('leave_from_time');
                const toTimeEl = document.getElementById('leave_to_time');
                if (!(fromDateEl && toDateEl && fromTimeEl && toTimeEl)) return;

                const fd = fromDateEl.value;
                const td = toDateEl.value;
                let ft = fromTimeEl.value || '00:00';
                let tt = toTimeEl.value || '00:00';

                if (!fd || !td) return;

                // Xử lý định dạng thời gian có SA/CH
                ft = normalizeTimeFormat(ft);
                tt = normalizeTimeFormat(tt);

                const start = new Date(`${fd}T${ft}:00`);
                const end = new Date(`${td}T${tt}:00`);

                if (!isNaN(start.getTime()) && !isNaN(end.getTime()) && start < end) {
                    // Kiểm tra thêm: Giờ kết thúc không được vượt quá giờ ra khỏi ca
                    const shiftCode = document.getElementById('leave_shift_code').value;
                    const shiftRanges = {
                        '1': { start: '07:30', end: '16:30' },
                        '2': { start: '09:00', end: '18:00' },
                        '3': { start: '11:00', end: '20:00' },
                        '4': { start: '08:00', end: '17:00' }
                    };

                    let isShiftTimeInvalid = false;
                    if (shiftCode in shiftRanges) { // Kiểm tra ngay cả khi chưa chọn ngày
                        const shiftStartTime = shiftRanges[shiftCode].start;
                        const shiftEndTime = shiftRanges[shiftCode].end;
                        const shiftStartMinutes = timeToMinutes(shiftStartTime);
                        const shiftEndMinutes = timeToMinutes(shiftEndTime);
                        const fromTimeMinutes = timeToMinutes(ft);
                        const toTimeMinutes = timeToMinutes(tt);

                        // Kiểm tra giờ bắt đầu không được trước giờ vào ca (chỉ khi có giờ bắt đầu)
                        if (ft && fromTimeMinutes < shiftStartMinutes) {
                            fromTimeEl.classList.add('is-invalid');
                            isShiftTimeInvalid = true;
                            try { showToast(`❌ Giờ bắt đầu: ${ft} → Lỗi "không được trước giờ vào ca (${shiftStartTime})"`, 'error'); } catch (_) { }
                        }

                        // Kiểm tra giờ kết thúc không được vượt quá giờ ra khỏi ca (chỉ khi có giờ kết thúc)
                        if (tt && toTimeMinutes > shiftEndMinutes) {
                            toTimeEl.classList.add('is-invalid');
                            isShiftTimeInvalid = true;
                            try { showToast(`❌ Giờ kết thúc: ${tt} → Lỗi "không được vượt quá giờ ra khỏi ca (${shiftEndTime})"`, 'error'); } catch (_) { }
                        }
                    }

                    if (!isShiftTimeInvalid) {
                        fromDateEl.classList.remove('is-invalid');
                        toDateEl.classList.remove('is-invalid');
                        fromTimeEl.classList.remove('is-invalid');
                        toTimeEl.classList.remove('is-invalid');
                        isDateTimeRangeInvalid = false;
                        updateTotalDays();
                    }
                }
            }

            // Hàm helper để xử lý định dạng thời gian
            function normalizeTimeFormat(timeStr) {
                if (!timeStr) return '00:00';

                // Xử lý đặc biệt cho các trường hợp 12:00
                if (timeStr.includes('12:00')) {
                    // 12:00 SA = 12:00 trưa (PM) - trong tiếng Việt
                    if (timeStr.includes('SA')) {
                        return '12:00';
                    }
                    // 12:00 CH = 12:00 chiều (PM) - trong tiếng Việt  
                    if (timeStr.includes('CH')) {
                        return '12:00';
                    }
                    // 12:00 PM = 12:00 trưa (PM) - chuẩn quốc tế
                    if (timeStr.includes('PM')) {
                        return '12:00';
                    }
                    // 12:00 AM = 00:00 nửa đêm (AM) - chuẩn quốc tế
                    if (timeStr.includes('AM')) {
                        return '00:00';
                    }
                }

                // Xử lý định dạng thời gian có SA/CH/AM/PM
                return timeStr.replace(/\s*(SA|CH|AM|PM)\s*/gi, '').trim();
            }

            // Debug function để kiểm tra thời gian
            function debugTimeValidation() {
                const fromTimeEl = document.getElementById('leave_from_time');
                const toTimeEl = document.getElementById('leave_to_time');

                if (fromTimeEl && toTimeEl) {
                    console.log('=== DEBUG TIME VALIDATION ===');
                    console.log('From time raw:', fromTimeEl.value);
                    console.log('From time normalized:', normalizeTimeFormat(fromTimeEl.value));
                    console.log('To time raw:', toTimeEl.value);
                    console.log('To time normalized:', normalizeTimeFormat(toTimeEl.value));

                    const fromTime = normalizeTimeFormat(fromTimeEl.value);
                    const toTime = normalizeTimeFormat(toTimeEl.value);

                    const start = new Date(`2024-01-01T${fromTime}:00`);
                    const end = new Date(`2024-01-01T${toTime}:00`);

                    console.log('Start datetime:', start);
                    console.log('End datetime:', end);
                    console.log('Is valid (start < end):', start < end);
                    console.log('================================');
                }
            }

            // Cập nhật khi thay đổi ngày
            if (leaveFromDate) leaveFromDate.addEventListener('change', () => {
                enforceDateRange(false);
                validateDateTimeSilent();
                checkShiftSelectionOnDateChange(); // Kiểm tra ca làm việc khi chọn ngày
                updateTotalDays();
            });
            if (leaveToDate) leaveToDate.addEventListener('change', () => {
                enforceDateRange(false);
                validateDateTimeSilent();
                checkShiftSelectionOnDateChange(); // Kiểm tra ca làm việc khi chọn ngày
                updateTotalDays();
            });
            // Cập nhật realtime khi đang gõ để xóa cảnh báo ngay khi hợp lệ
            if (leaveFromDate) leaveFromDate.addEventListener('blur', () => { enforceDateRange(false); validateDateTimeSilent(); });
            if (leaveToDate) leaveToDate.addEventListener('blur', () => { enforceDateRange(false); validateDateTimeSilent(); });

            // Cảnh báo ngay khi rời ô (blur) nếu phạm vi ngày không hợp lệ
            function warnIfDateInvalid(target) {
                if (!leaveFromDate || !leaveToDate) return;
                const from = leaveFromDate.value ? new Date(leaveFromDate.value) : null;
                const to = leaveToDate.value ? new Date(leaveToDate.value) : null;
                if (from && to && from > to) {
                    // Khoanh đỏ 2 ô ngày khi sai
                    leaveFromDate.classList.add('is-invalid');
                    leaveToDate.classList.add('is-invalid');
                    isDateTimeRangeInvalid = true;
                    try { showToast('Ngày kết thúc phải lớn hơn hoặc bằng ngày bắt đầu', 'error'); } catch (_) { }
                    updateTotalDays();
                } else {
                    leaveFromDate.classList.remove('is-invalid');
                    leaveToDate.classList.remove('is-invalid');
                }
            }
            if (leaveToDate) leaveToDate.addEventListener('blur', () => { enforceDateRange(true); warnIfDateInvalid(leaveToDate); });
            if (leaveFromDate) leaveFromDate.addEventListener('blur', () => { enforceDateRange(true); warnIfDateInvalid(leaveFromDate); });
            const fromTimeEl = document.getElementById('leave_from_time');
            const toTimeEl = document.getElementById('leave_to_time');
            if (fromTimeEl) {
                fromTimeEl.addEventListener('change', () => { debugTimeValidation(); validateDateTimeSilent(); updateTotalDays(); });
                // Chỉ validate khi blur để giảm thiểu spam
                fromTimeEl.addEventListener('blur', () => { debugTimeValidation(); validateDateTimeSilent(); updateTotalDays(); });
            }
            if (toTimeEl) {
                toTimeEl.addEventListener('change', () => { debugTimeValidation(); validateDateTimeSilent(); updateTotalDays(); });
                // Chỉ validate khi blur để giảm thiểu spam
                toTimeEl.addEventListener('blur', () => {
                    debugTimeValidation();
                    validateDateTimeOnBlur();
                    updateImage2WithDateData(); // Cập nhật hình 2 với dữ liệu ngày

                    // Sau khi người dùng rời ô "Đến giờ", tính lại khoảng thời gian thực tế
                    // và nếu là số ngày lẻ (0.5, 1.5, 2.5, ...) thì hỏi có sử dụng giờ nghỉ trưa không
                    try {
                        const requestTypeSelect = document.getElementById('requestTypeSelect');
                        if (!requestTypeSelect || requestTypeSelect.value !== 'leave') {
                            return; // Chỉ áp dụng cho đơn nghỉ phép
                        }

                        const fromDateVal = leaveFromDate ? leaveFromDate.value : '';
                        const toDateVal = leaveToDate ? leaveToDate.value : '';
                        const fromTimeVal = fromTimeEl ? fromTimeEl.value : '';
                        const toTimeVal = toTimeEl.value || '';
                        const shiftCodeEl = document.getElementById('leave_shift_code');
                        const shiftCode = shiftCodeEl ? shiftCodeEl.value : '';

                        if (!fromDateVal || !toDateVal || !fromTimeVal || !toTimeVal || !shiftCode) {
                            return;
                        }

                        const fromDateObj = new Date(fromDateVal);
                        const toDateObj = new Date(toDateVal);
                        const normFromTime = normalizeTimeFormat(fromTimeVal);
                        const normToTime = normalizeTimeFormat(toTimeVal);

                        const calcFn = window.calculateActualLeaveDays || calculateActualLeaveDays;
                        if (typeof calcFn !== 'function') return;

                        const actualLeaveDays = calcFn(fromDateObj, toDateObj, normFromTime, normToTime, shiftCode);
                        if (!actualLeaveDays || isNaN(actualLeaveDays)) return;

                        const fractional = Math.abs(actualLeaveDays - Math.round(actualLeaveDays));
                        // Nếu là số nguyên (1, 2, 3, ...) thì không cần hỏi
                        if (fractional < 1e-6) return;

                        // Tạo/ghi hidden input lưu lựa chọn dùng giờ nghỉ trưa
                        const formEl = document.getElementById('leaveRequestForm');
                        if (!formEl || typeof Swal === 'undefined') return;

                        let lunchInput = document.getElementById('use_lunch_break');
                        if (!lunchInput) {
                            lunchInput = document.createElement('input');
                            lunchInput.type = 'hidden';
                            lunchInput.name = 'use_lunch_break';
                            lunchInput.id = 'use_lunch_break';
                            formEl.appendChild(lunchInput);
                        }

                        Swal.fire({
                            title: 'Bạn có sử dụng giờ nghỉ trưa không vào 0.5 ngày đó không?',
                            text: `Khoảng thời gian thực tế: ${actualLeaveDays} ngày (tính theo ca ${shiftCode}).`,
                            icon: 'question',
                            showCancelButton: true,
                            confirmButtonText: 'Có, dùng giờ nghỉ trưa',
                            cancelButtonText: 'Không dùng giờ nghỉ trưa',
                            reverseButtons: true,
                            allowOutsideClick: false,
                            allowEscapeKey: false,
                            allowEnterKey: true
                        }).then((result) => {
                            lunchInput.value = result.isConfirmed ? 'true' : 'false';
                        });
                    } catch (e) {
                        console.warn('Error handling lunch break confirmation:', e);
                    }
                });
            }
            if (document.getElementById('leave_shift_code')) document.getElementById('leave_shift_code').addEventListener('change', updateTotalDays);

            // Hiển thị trường động theo nhóm Scope/York (cùng hàng với các ô ngày phép)
            if (teamEl) {
                const applyTeamFields = () => {
                    const val = (teamEl.value || teamEl.getAttribute('value') || teamEl.textContent || '').toLowerCase().trim();
                    const includes = (s) => val.indexOf(s) !== -1;
                    if (val === 'scope' || includes('scope')) {
                        if (scopeWrap) scopeWrap.style.display = '';
                        if (yorkWrap) yorkWrap.style.display = 'none';
                    } else if (val === 'york' || includes('york')) {
                        if (scopeWrap) scopeWrap.style.display = 'none';
                        if (yorkWrap) yorkWrap.style.display = '';
                    } else {
                        if (scopeWrap) scopeWrap.style.display = 'none';
                        if (yorkWrap) yorkWrap.style.display = 'none';
                    }
                };
                applyTeamFields();
                teamEl.addEventListener('change', applyTeamFields);
            }

            // Hàm validation tổng quát - kiểm tra tất cả lỗi có thể xảy ra
            window.validateAllFields = function () {
                let hasErrors = false;
                let errorMessages = [];

                // 0. Kiểm tra validation đặc biệt cho đi trễ/về sớm
                const lateEarlyValidation = validateLateEarlyMode();
                if (lateEarlyValidation.hasErrors) {
                    hasErrors = true;
                    errorMessages.push(...lateEarlyValidation.errorMessages);
                }

                // 0.1. Kiểm tra validation đặc biệt cho nghỉ 30 phút
                const break30MinValidation = validate30MinBreakMode();
                if (break30MinValidation.hasErrors) {
                    hasErrors = true;
                    errorMessages.push(...break30MinValidation.errorMessages);
                }

                // 1. Kiểm tra các trường bắt buộc
                const requestType = document.getElementById('requestTypeSelect').value;
                const isLateEarly = requestType !== 'leave';
                const requiredFields = ['employee_name', 'team', 'employee_code', 'leave_from_date', 'leave_from_time', 'leave_to_date', 'leave_to_time', 'leave_shift_code'];

                // Chỉ yêu cầu lý do cho nghỉ phép và đi trễ/về sớm, không yêu cầu cho nghỉ 30 phút
                if (requestType !== '30min_break') {
                    requiredFields.push('leave_reason');
                }

                // Thêm trường loại đi trễ/về sớm nếu cần
                if (requestType === 'late_early') {
                    requiredFields.push('late_early_type');
                }

                for (let field of requiredFields) {
                    const element = document.getElementById(field);
                    if (!element || !element.value || element.value.trim() === '') {
                        // Kiểm tra xem element có bị ẩn không
                        if (element && element.closest('.col-md-6') && element.closest('.col-md-6').style.display === 'none') {
                            continue; // Bỏ qua validation cho trường bị ẩn
                        }

                        hasErrors = true;
                        element.classList.add('is-invalid');
                        errorMessages.push(`Trường ${getFieldDisplayName(field)} là bắt buộc`);
                    } else {
                        element.classList.remove('is-invalid');
                    }
                }

                // 2. Kiểm tra khoảng thời gian hợp lệ
                const fromDateEl = document.getElementById('leave_from_date');
                const toDateEl = document.getElementById('leave_to_date');
                const fromTimeEl = document.getElementById('leave_from_time');
                const toTimeEl = document.getElementById('leave_to_time');

                if (fromDateEl.value && toDateEl.value && fromTimeEl.value && toTimeEl.value) {
                    const fromDate = new Date(fromDateEl.value);
                    const toDate = new Date(toDateEl.value);
                    let fromTime = normalizeTimeFormat(fromTimeEl.value);
                    let toTime = normalizeTimeFormat(toTimeEl.value);

                    const start = new Date(`${fromDateEl.value}T${fromTime}:00`);
                    const end = new Date(`${toDateEl.value}T${toTime}:00`);

                    if (start >= end) {
                        hasErrors = true;
                        fromDateEl.classList.add('is-invalid');
                        toDateEl.classList.add('is-invalid');
                        fromTimeEl.classList.add('is-invalid');
                        toTimeEl.classList.add('is-invalid');
                        errorMessages.push('Thời gian từ ngày giờ phải nhỏ hơn đến ngày giờ');
                    }
                }

                // 2.1. Kiểm tra giờ nghỉ phép có trong khung giờ ca làm việc
                const selectedShiftCode = document.getElementById('leave_shift_code').value;
                if (selectedShiftCode && (fromTimeEl.value || toTimeEl.value)) { // Kiểm tra khi có giờ được nhập
                    const shiftRanges = {
                        '1': { start: '07:30', end: '16:30' },
                        '2': { start: '09:00', end: '18:00' },
                        '3': { start: '11:00', end: '20:00' },
                        '4': { start: '08:00', end: '17:00' }
                    };

                    if (selectedShiftCode in shiftRanges) {
                        const shiftStartTime = shiftRanges[selectedShiftCode].start;
                        const shiftEndTime = shiftRanges[selectedShiftCode].end;
                        const shiftStartMinutes = timeToMinutes(shiftStartTime);
                        const shiftEndMinutes = timeToMinutes(shiftEndTime);
                        const fromTimeValue = normalizeTimeFormat(fromTimeEl.value);
                        const toTimeValue = normalizeTimeFormat(toTimeEl.value);
                        const fromTimeMinutes = timeToMinutes(fromTimeValue);
                        const toTimeMinutes = timeToMinutes(toTimeValue);

                        // Kiểm tra giờ bắt đầu không được trước giờ vào ca (chỉ khi có giờ bắt đầu)
                        if (fromTimeEl.value && fromTimeMinutes < shiftStartMinutes) {
                            hasErrors = true;
                            fromTimeEl.classList.add('is-invalid');
                            errorMessages.push(`❌ Giờ bắt đầu: ${fromTimeValue} → Lỗi "không được trước giờ vào ca (${shiftStartTime})"`);
                        }

                        // Kiểm tra giờ kết thúc không được vượt quá giờ ra khỏi ca (chỉ khi có giờ kết thúc)
                        if (toTimeEl.value && toTimeMinutes > shiftEndMinutes) {
                            hasErrors = true;
                            toTimeEl.classList.add('is-invalid');
                            errorMessages.push(`❌ Giờ kết thúc: ${toTimeValue} → Lỗi "không được vượt quá giờ ra khỏi ca (${shiftEndTime})"`);
                        }
                    }
                }

                // 3. Kiểm tra số ngày nghỉ hợp lệ (chỉ cho nghỉ phép)
                let totalDays = 0;
                if (!isLateEarly) {
                    const annualDays = parseFloat(document.getElementById('annual_leave_days').value || '0');
                    const unpaidDays = parseFloat(document.getElementById('unpaid_leave_days').value || '0');
                    const specialDays = parseFloat(document.getElementById('special_leave_days').value || '0');
                    totalDays = annualDays + unpaidDays + specialDays;

                    if (totalDays <= 0) {
                        hasErrors = true;
                        errorMessages.push('Tổng số ngày xin nghỉ phải lớn hơn 0');
                    }

                    // 4. Kiểm tra số ngày nghỉ phải là bội số của 0.5
                    const dayFields = ['annual_leave_days', 'unpaid_leave_days', 'special_leave_days'];
                    for (let field of dayFields) {
                        const value = document.getElementById(field).value;
                        if (value && !((parseFloat(value) * 2) % 1 === 0)) {
                            hasErrors = true;
                            document.getElementById(field).classList.add('is-invalid');
                            errorMessages.push('Số ngày nghỉ phải là bội số của 0.5 (ví dụ 0.5, 1, 1.5)');
                        }
                    }
                }

                // 5. Kiểm tra tổng số ngày xin nghỉ phải bằng khoảng thời gian thực tế (chỉ cho nghỉ phép)
                if (!isLateEarly) {
                    const shiftCode = document.getElementById('leave_shift_code').value;
                    if (shiftCode && fromDateEl.value && toDateEl.value && fromTimeEl.value && toTimeEl.value) {
                        const fromDate = new Date(fromDateEl.value);
                        const toDate = new Date(toDateEl.value);
                        const fromTime = normalizeTimeFormat(fromTimeEl.value);
                        const toTime = normalizeTimeFormat(toTimeEl.value);

                        const actualLeaveDays = calculateActualLeaveDays(fromDate, toDate, fromTime, toTime, shiftCode);

                        if (totalDays !== actualLeaveDays) {
                            hasErrors = true;
                            if (totalDays > actualLeaveDays) {
                                errorMessages.push(`Bạn đã xin quá nhiều! Cần giảm xuống còn ${actualLeaveDays} ngày để gửi đơn.`);
                            } else {
                                errorMessages.push(`Bạn chưa xin đủ! Cần thêm ${actualLeaveDays - totalDays} ngày nữa để gửi đơn.`);
                            }
                        }
                    }
                }

                return {
                    hasErrors: hasErrors,
                    errorMessages: errorMessages
                };
            };

            // Hàm helper để lấy tên hiển thị của field
            function getFieldDisplayName(fieldId) {
                const fieldNames = {
                    'employee_name': 'Họ và tên',
                    'team': 'Nhóm',
                    'employee_code': 'Mã nhân viên',
                    'leave_reason': 'Lý do nghỉ phép',
                    'leave_from_date': 'Từ ngày',
                    'leave_from_time': 'Từ giờ',
                    'leave_to_date': 'Đến ngày',
                    'leave_to_time': 'Đến giờ',
                    'leave_shift_code': 'Ca làm việc'
                };
                return fieldNames[fieldId] || fieldId;
            }

            // Hàm test validation cho tất cả các ca làm việc
            function testAllShiftValidations() {
                console.log('=== TEST VALIDATION CHO TẤT CẢ CÁC CA ===');

                const shiftRanges = {
                    '1': { start: '07:30', end: '16:30' },
                    '2': { start: '09:00', end: '18:00' },
                    '3': { start: '11:00', end: '20:00' },
                    '4': { start: '08:00', end: '17:00' }
                };

                // Test cases cho từng ca
                const testCases = [
                    // Ca 1 (07:30 - 16:30)
                    { shift: '1', fromTime: '06:30', toTime: '16:30', expectedFromError: true, expectedToError: false },
                    { shift: '1', fromTime: '07:30', toTime: '17:30', expectedFromError: false, expectedToError: true },
                    { shift: '1', fromTime: '08:00', toTime: '15:00', expectedFromError: false, expectedToError: false },

                    // Ca 2 (09:00 - 18:00)
                    { shift: '2', fromTime: '08:30', toTime: '18:00', expectedFromError: true, expectedToError: false },
                    { shift: '2', fromTime: '09:00', toTime: '19:00', expectedFromError: false, expectedToError: true },
                    { shift: '2', fromTime: '10:00', toTime: '17:00', expectedFromError: false, expectedToError: false },

                    // Ca 3 (11:00 - 20:00)
                    { shift: '3', fromTime: '10:30', toTime: '20:00', expectedFromError: true, expectedToError: false },
                    { shift: '3', fromTime: '11:00', toTime: '21:00', expectedFromError: false, expectedToError: true },
                    { shift: '3', fromTime: '12:00', toTime: '19:00', expectedFromError: false, expectedToError: false },

                    // Ca 4 (08:00 - 17:00)
                    { shift: '4', fromTime: '07:30', toTime: '17:00', expectedFromError: true, expectedToError: false },
                    { shift: '4', fromTime: '08:00', toTime: '18:00', expectedFromError: false, expectedToError: true },
                    { shift: '4', fromTime: '09:00', toTime: '16:00', expectedFromError: false, expectedToError: false }
                ];

                testCases.forEach((testCase, index) => {
                    const shift = shiftRanges[testCase.shift];
                    const shiftStartMinutes = timeToMinutes(shift.start);
                    const shiftEndMinutes = timeToMinutes(shift.end);
                    const fromTimeMinutes = timeToMinutes(testCase.fromTime);
                    const toTimeMinutes = timeToMinutes(testCase.toTime);

                    const fromError = fromTimeMinutes < shiftStartMinutes;
                    const toError = toTimeMinutes > shiftEndMinutes;

                    const fromMatch = fromError === testCase.expectedFromError;
                    const toMatch = toError === testCase.expectedToError;

                    console.log(`Test ${index + 1} - Ca ${testCase.shift} (${shift.start} - ${shift.end}):`);
                    console.log(`  Input: ${testCase.fromTime} - ${testCase.toTime}`);
                    console.log(`  From Error: ${fromError} (expected: ${testCase.expectedFromError}) ${fromMatch ? '✅' : '❌'}`);
                    console.log(`  To Error: ${toError} (expected: ${testCase.expectedToError}) ${toMatch ? '✅' : '❌'}`);
                    console.log(`  Result: ${fromMatch && toMatch ? '✅ PASS' : '❌ FAIL'}`);
                    console.log('---');
                });

                console.log('=== KẾT THÚC TEST ===');
            }

            // Gọi hàm test khi trang load (chỉ trong development)
            if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
                setTimeout(testAllShiftValidations, 1000);
            }

            // ===== LOGIC XỬ LÝ TOGGLE GIỮA NGHỈ PHÉP VÀ ĐI TRỄ/VỀ SỚM =====

            // Hàm cập nhật giao diện theo loại đơn
            window.updateFormMode = function (requestType) {
                const reasonLabel = document.getElementById('reasonLabel');
                const fromDateLabel = document.getElementById('fromDateLabel');
                const toDateLabel = document.getElementById('toDateLabel');
                const lateEarlyTypeSection = document.getElementById('lateEarlyTypeSection');
                const attachmentsSection = document.getElementById('attachmentsSection');
                const attachmentGuidelinesSection = document.getElementById('attachmentGuidelinesSection');
                const reasonSectionTitle = document.getElementById('reasonSectionTitle');
                const leaveDaysSection = document.getElementById('leaveDaysSection');
                const replacementSection = document.getElementById('replacementSection');
                const requestTypeInput = document.getElementById('requestType');
                const leaveReasonTextarea = document.getElementById('leave_reason');
                const notesSection = document.querySelector('.form-section:has(#notes)');
                const reasonFieldSection = leaveReasonTextarea.closest('.col-md-6');

                if (requestType === 'late_early') {
                    // Chế độ đi trễ/về sớm
                    reasonLabel.innerHTML = 'Lý do đi trễ/về sớm <span class="required">*</span>'; // Có dấu sao
                    fromDateLabel.textContent = 'Ngày đi trễ/về sớm';
                    toDateLabel.textContent = 'Thời gian đi trễ/về sớm';
                    lateEarlyTypeSection.style.display = 'block';
                    attachmentsSection.style.display = 'none'; // Ẩn phần chứng từ
                    attachmentGuidelinesSection.style.display = 'none'; // Ẩn phần hướng dẫn chứng từ
                    reasonSectionTitle.innerHTML = '<i class="fas fa-clipboard-list"></i> Lý do nghỉ phép'; // Thay đổi title
                    leaveDaysSection.style.display = 'none'; // Ẩn phần số ngày nghỉ
                    replacementSection.style.display = 'none'; // Ẩn phần người thay thế
                    requestTypeInput.value = 'late_early';
                    leaveReasonTextarea.placeholder = 'Vui lòng mô tả chi tiết lý do đi trễ/về sớm...';
                    leaveReasonTextarea.setAttribute('required', 'required'); // Có thuộc tính required

                    // Hiện lại trường lý do cho đi trễ/về sớm
                    if (reasonFieldSection) {
                        reasonFieldSection.style.display = 'block';
                        leaveReasonTextarea.setAttribute('required', 'required'); // Đảm bảo có thuộc tính required
                    }

                    // Cập nhật title trang
                    document.title = document.title.replace('nghỉ phép', 'đi trễ/về sớm');

                } else if (requestType === '30min_break') {
                    // Chế độ nghỉ 30 phút
                    fromDateLabel.textContent = 'Ngày nghỉ';
                    toDateLabel.textContent = 'Thời gian nghỉ';
                    lateEarlyTypeSection.style.display = 'none';
                    attachmentsSection.style.display = 'none'; // Ẩn phần chứng từ
                    attachmentGuidelinesSection.style.display = 'none'; // Ẩn phần hướng dẫn chứng từ
                    reasonSectionTitle.innerHTML = '<i class="fas fa-clock"></i> Nghỉ 30 phút (dành cho nữ)';
                    leaveDaysSection.style.display = 'none'; // Ẩn phần số ngày nghỉ
                    replacementSection.style.display = 'none'; // Ẩn phần người thay thế
                    requestTypeInput.value = '30min_break';

                    // Ẩn hoàn toàn trường lý do cho nghỉ 30 phút và loại bỏ required
                    if (reasonFieldSection) {
                        reasonFieldSection.style.display = 'none';
                        leaveReasonTextarea.removeAttribute('required'); // Loại bỏ thuộc tính required
                        leaveReasonTextarea.value = 'Nghỉ 30 phút';
                    }

                    // Ẩn phần ghi chú cho nghỉ 30 phút
                    if (notesSection) {
                        notesSection.style.display = 'none';
                    }

                    // Cập nhật title trang
                    document.title = document.title.replace('nghỉ phép', 'nghỉ 30 phút');

                } else {
                    // Chế độ nghỉ phép thông thường
                    reasonLabel.innerHTML = 'Lý do nghỉ phép <span class="required">*</span>'; // Khôi phục dấu sao
                    fromDateLabel.textContent = 'Từ ngày (Sau 11:59 là CH)';
                    toDateLabel.textContent = 'Đến ngày (Sau 11:59 là CH)';
                    lateEarlyTypeSection.style.display = 'none';
                    attachmentsSection.style.display = 'block'; // Hiện phần chứng từ
                    attachmentGuidelinesSection.style.display = 'block'; // Hiện phần hướng dẫn chứng từ
                    reasonSectionTitle.innerHTML = '<i class="fas fa-clipboard-list"></i> Lý do nghỉ phép & Chứng từ đính kèm'; // Khôi phục title
                    leaveDaysSection.style.display = 'block'; // Hiện phần số ngày nghỉ
                    replacementSection.style.display = 'block'; // Hiện phần người thay thế
                    requestTypeInput.value = 'leave';
                    leaveReasonTextarea.placeholder = 'Vui lòng mô tả chi tiết lý do nghỉ phép...';
                    leaveReasonTextarea.setAttribute('required', 'required'); // Khôi phục thuộc tính required

                    // Hiện lại trường lý do cho nghỉ phép thông thường
                    if (reasonFieldSection) {
                        reasonFieldSection.style.display = 'block';
                        leaveReasonTextarea.setAttribute('required', 'required'); // Khôi phục thuộc tính required
                    }

                    // Hiện phần ghi chú cho nghỉ phép thông thường
                    if (notesSection) {
                        notesSection.style.display = 'block';
                    }

                    // Cập nhật title trang
                    document.title = document.title.replace('đi trễ/về sớm', 'nghỉ phép');
                    document.title = document.title.replace('nghỉ 30 phút', 'nghỉ phép');

                }
            }

            // Event listener cho dropdown loại đơn
            document.getElementById('requestTypeSelect').addEventListener('change', function () {
                const requestType = this.value;
                window.updateFormMode(requestType);

                // Hiển thị toast thông báo
                try {
                    let modeText = 'Nghỉ phép';
                    if (requestType === 'late_early') modeText = 'Đi trễ/Về sớm';
                    else if (requestType === '30min_break') modeText = 'Nghỉ 30 phút (dành cho nữ)';
                    showToast(`🔄 Đã chuyển sang chế độ: ${modeText}`, 'info');
                } catch (_) { }
            });

            // Debounce mechanism để tránh validation quá nhiều
            let validationTimeout;
            function debouncedValidation(callback, delay = 500) {
                clearTimeout(validationTimeout);
                validationTimeout = setTimeout(callback, delay);
            }

            // Event listener cho validation real-time của nghỉ 30 phút
            const timeInputsForValidation = ['leave_from_time', 'leave_to_time', 'leave_from_date', 'leave_to_date'];
            timeInputsForValidation.forEach(inputId => {
                const input = document.getElementById(inputId);
                if (input) {
                    input.addEventListener('change', function () {
                        const requestType = document.getElementById('requestTypeSelect').value;
                        if (requestType === '30min_break') {
                            // Sử dụng debounce để tránh validation quá nhiều
                            debouncedValidation(() => {
                                // Chỉ validate khi đã nhập đủ cả ngày và giờ
                                const fromDate = document.getElementById('leave_from_date').value;
                                const toDate = document.getElementById('leave_to_date').value;
                                const fromTime = document.getElementById('leave_from_time').value;
                                const toTime = document.getElementById('leave_to_time').value;

                                // Chỉ validate khi có đủ thông tin
                                if (fromDate && toDate && fromTime && toTime) {
                                    const validation = validate30MinBreakMode();
                                    if (validation.hasErrors) {
                                        // Hiển thị lỗi real-time
                                        showToast(validation.errorMessages.join('\n• '), 'error');
                                    }
                                }
                            }, 300); // Delay 300ms
                        }
                    });
                }
            });

            // Khởi tạo chế độ ban đầu
            const initialMode = document.getElementById('requestTypeSelect').value;
            window.updateFormMode(initialMode);

            // Hàm validation chứng từ đính kèm
            // Hàm validation đặc biệt cho nghỉ 30 phút
            function validate30MinBreakMode() {
                const requestType = document.getElementById('requestTypeSelect').value;
                if (requestType !== '30min_break') return { hasErrors: false, errorMessages: [] };

                const fromDate = document.getElementById('leave_from_date').value;
                const toDate = document.getElementById('leave_to_date').value;
                const fromTime = document.getElementById('leave_from_time').value;
                const toTime = document.getElementById('leave_to_time').value;

                let hasErrors = false;
                let errorMessages = [];

                // Kiểm tra ngày nghỉ phải cùng ngày (kiểm tra trước)
                if (fromDate && toDate && fromDate !== toDate) {
                    hasErrors = true;
                    errorMessages.push('❌ Nghỉ 30 phút phải trong cùng 1 ngày');
                }

                // Kiểm tra thời gian nghỉ phải là chính xác 30 phút
                if (fromTime && toTime) {
                    const fromTimeParts = fromTime.split(':');
                    const toTimeParts = toTime.split(':');

                    // Kiểm tra format thời gian hợp lệ
                    if (fromTimeParts.length !== 2 || toTimeParts.length !== 2) {
                        hasErrors = true;
                        errorMessages.push('❌ Định dạng thời gian không hợp lệ');
                        return { hasErrors, errorMessages };
                    }

                    const fromHour = parseInt(fromTimeParts[0]);
                    const fromMinute = parseInt(fromTimeParts[1]);
                    const toHour = parseInt(toTimeParts[0]);
                    const toMinute = parseInt(toTimeParts[1]);

                    // Kiểm tra giá trị thời gian hợp lệ
                    if (isNaN(fromHour) || isNaN(fromMinute) || isNaN(toHour) || isNaN(toMinute)) {
                        hasErrors = true;
                        errorMessages.push('❌ Thời gian không hợp lệ');
                        return { hasErrors, errorMessages };
                    }

                    if (fromHour < 0 || fromHour > 23 || fromMinute < 0 || fromMinute > 59 ||
                        toHour < 0 || toHour > 23 || toMinute < 0 || toMinute > 59) {
                        hasErrors = true;
                        errorMessages.push('❌ Thời gian không hợp lệ (giờ: 0-23, phút: 0-59)');
                        return { hasErrors, errorMessages };
                    }

                    const fromMinutes = fromHour * 60 + fromMinute;
                    const toMinutes = toHour * 60 + toMinute;
                    const diffMinutes = toMinutes - fromMinutes;

                    // Kiểm tra thời gian nghỉ phải là chính xác 30 phút
                    if (diffMinutes !== 30) {
                        hasErrors = true;
                        errorMessages.push('❌ Nghỉ 30 phút phải có thời gian chính xác là 30 phút');
                    }

                    // Kiểm tra thời gian kết thúc phải sau thời gian bắt đầu
                    if (diffMinutes <= 0) {
                        hasErrors = true;
                        errorMessages.push('❌ Thời gian kết thúc phải sau thời gian bắt đầu');
                    }
                } else {
                    // Nếu thiếu thời gian - không hiển thị lỗi để tránh spam
                    // Chỉ validate khi đã có đủ thông tin
                    return { hasErrors: false, errorMessages: [] };
                }

                return { hasErrors, errorMessages };
            }

            // Hàm validation đặc biệt cho đi trễ/về sớm
            function validateLateEarlyMode() {
                const requestType = document.getElementById('requestTypeSelect').value;
                if (requestType !== 'late_early') return true; // Không cần validation đặc biệt cho nghỉ phép và nghỉ 30 phút

                const lateEarlyType = document.getElementById('late_early_type').value;
                const fromDate = document.getElementById('leave_from_date').value;
                const toDate = document.getElementById('leave_to_date').value;
                const fromTime = document.getElementById('leave_from_time').value;
                const toTime = document.getElementById('leave_to_time').value;

                let hasErrors = false;
                let errorMessages = [];

                // Kiểm tra loại đi trễ/về sớm
                if (!lateEarlyType) {
                    hasErrors = true;
                    document.getElementById('late_early_type').classList.add('is-invalid');
                    errorMessages.push('❌ Vui lòng chọn loại: Đi trễ hoặc Về sớm');
                } else {
                    document.getElementById('late_early_type').classList.remove('is-invalid');
                }

                // Kiểm tra ngày (đi trễ/về sớm thường chỉ trong 1 ngày)
                if (fromDate && toDate && fromDate !== toDate) {
                    hasErrors = true;
                    document.getElementById('leave_to_date').classList.add('is-invalid');
                    errorMessages.push('❌ Đi trễ/về sớm chỉ áp dụng trong cùng 1 ngày');
                } else {
                    document.getElementById('leave_to_date').classList.remove('is-invalid');
                }

                // Kiểm tra logic đi trễ/về sớm
                if (lateEarlyType === 'late' && fromTime && toTime) {
                    // Đi trễ: thời gian bắt đầu phải sau thời gian kết thúc (vì là cùng ngày)
                    const fromMinutes = timeToMinutes(fromTime);
                    const toMinutes = timeToMinutes(toTime);
                    if (fromMinutes >= toMinutes) {
                        hasErrors = true;
                        document.getElementById('leave_from_time').classList.add('is-invalid');
                        errorMessages.push('❌ Đi trễ: Thời gian bắt đầu phải trước thời gian kết thúc');
                    }
                } else if (lateEarlyType === 'early' && fromTime && toTime) {
                    // Về sớm: thời gian bắt đầu phải trước thời gian kết thúc
                    const fromMinutes = timeToMinutes(fromTime);
                    const toMinutes = timeToMinutes(toTime);
                    if (fromMinutes >= toMinutes) {
                        hasErrors = true;
                        document.getElementById('leave_to_time').classList.add('is-invalid');
                        errorMessages.push('❌ Về sớm: Thời gian bắt đầu phải trước thời gian kết thúc');
                    }
                }

                return {
                    hasErrors: hasErrors,
                    errorMessages: errorMessages
                };
            }

            // Hàm kiểm tra ca làm việc khi chọn ngày
            function checkShiftSelectionOnDateChange() {
                const shiftSelect = document.getElementById('leave_shift_code');
                const fromDateEl = document.getElementById('leave_from_date');
                const toDateEl = document.getElementById('leave_to_date');

                if (!shiftSelect || !fromDateEl || !toDateEl) return;

                // Kiểm tra nếu đã chọn ngày mà chưa chọn ca
                if ((fromDateEl.value || toDateEl.value) && !shiftSelect.value) {
                    // Hiển thị lỗi trên dropdown ca làm việc
                    shiftSelect.classList.add('is-invalid');

                    // Hiển thị toast thông báo
                    try {
                        showToast('⚠️ Bạn đã chọn ngày nghỉ nhưng quên chọn ca làm việc! Vui lòng chọn ca làm việc trước.', 'warning');
                    } catch (_) { }

                    // Focus vào dropdown ca làm việc
                    setTimeout(() => {
                        shiftSelect.focus();
                    }, 100);
                } else if (shiftSelect.value) {
                    // Nếu đã chọn ca thì bỏ lỗi
                    shiftSelect.classList.remove('is-invalid');
                }
            }

            // Hàm helper để chuyển đổi thời gian thành phút
            function timeToMinutes(timeStr) {
                if (!timeStr) return 0;

                // Xử lý định dạng thời gian có thể có SA/CH/AM/PM
                let cleanTimeStr = timeStr.replace(/\s*(SA|CH|AM|PM)\s*/gi, '').trim();

                const [hours, minutes] = cleanTimeStr.split(':').map(Number);

                // Xử lý đặc biệt cho các trường hợp 12:00
                if (hours === 12) {
                    // 12:00 SA = 12:00 trưa (PM) - trong tiếng Việt
                    if (timeStr.includes('SA')) {
                        return 12 * 60 + minutes; // 720 phút
                    }
                    // 12:00 CH = 12:00 chiều (PM) - trong tiếng Việt
                    if (timeStr.includes('CH')) {
                        return 12 * 60 + minutes; // 720 phút
                    }
                    // 12:00 PM = 12:00 trưa (PM) - chuẩn quốc tế
                    if (timeStr.includes('PM')) {
                        return 12 * 60 + minutes; // 720 phút
                    }
                    // 12:00 AM = 00:00 nửa đêm (AM) - chuẩn quốc tế
                    if (timeStr.includes('AM')) {
                        return 0; // 0 phút
                    }
                }

                // Trả về số phút từ 00:00
                return hours * 60 + minutes;
            }

            // Hàm cập nhật hình 2 với dữ liệu ngày
            function updateImage2WithDateData() {
                console.log('=== updateImage2WithDateData được gọi ===');
                const fromDateEl = document.getElementById('leave_from_date');
                const toDateEl = document.getElementById('leave_to_date');
                const fromTimeEl = document.getElementById('leave_from_time');
                const toTimeEl = document.getElementById('leave_to_time');
                const shiftCodeEl = document.getElementById('leave_shift_code');

                console.log('Elements found:', {
                    fromDateEl: !!fromDateEl,
                    toDateEl: !!toDateEl,
                    fromTimeEl: !!fromTimeEl,
                    toTimeEl: !!toTimeEl,
                    shiftCodeEl: !!shiftCodeEl
                });

                if (!fromDateEl || !toDateEl || !fromTimeEl || !toTimeEl || !shiftCodeEl) {
                    console.log('Thiếu elements, return');
                    return;
                }

                const fromDate = fromDateEl.value;
                const toDate = toDateEl.value;
                const fromTime = fromTimeEl.value;
                const toTime = toTimeEl.value;
                const shiftCode = shiftCodeEl.value;

                console.log('Values:', { fromDate, toDate, fromTime, toTime, shiftCode });

                if (!fromDate || !toDate || !fromTime || !toTime) {
                    console.log('Thiếu values, return');
                    return;
                }

                // Tính toán khoảng thời gian thực tế
                const fromDateObj = new Date(fromDate);
                const toDateObj = new Date(toDate);
                const actualLeaveDays = shiftCode ? calculateActualLeaveDays(fromDateObj, toDateObj, fromTime, toTime, shiftCode) : 0;

                console.log('Actual leave days calculated:', actualLeaveDays);

                // Cập nhật text trong hình 2 (phần hiển thị khoảng thời gian thực tế)
                const requiredDaysElement = document.querySelector('.alert-info p:last-child');
                console.log('Required days element found:', !!requiredDaysElement);
                if (requiredDaysElement) {
                    const newText = `Khoảng thời gian thực tế: ${actualLeaveDays} ngày (tính theo ca ${shiftCode})`;
                    requiredDaysElement.innerHTML = newText;
                    console.log('Updated text:', newText);
                }

                // Cập nhật trạng thái ngày
                updateTotalDays();
                console.log('=== updateImage2WithDateData hoàn thành ===');
            }

            // Hàm tính toán khoảng thời gian thực tế sử dụng phép
            function calculateActualLeaveDays(fromDate, toDate, fromTime, toTime, shiftCode) {
                // Định nghĩa ca làm việc (bao gồm giờ nghỉ trưa)
                const shiftMap = {
                    '1': { start: '07:30', end: '16:30', breakStart: '11:30', breakEnd: '12:30' },
                    '2': { start: '09:00', end: '18:00', breakStart: '13:00', breakEnd: '14:00' },
                    '3': { start: '11:00', end: '20:00', breakStart: '15:00', breakEnd: '16:00' },
                    '4': { start: '08:00', end: '17:00', breakStart: '12:00', breakEnd: '13:00' }
                };

                const shift = shiftMap[shiftCode] || shiftMap['1'];
                const shiftStart = shift.start;
                const shiftEnd = shift.end;
                const breakStart = shift.breakStart;
                const breakEnd = shift.breakEnd;

                // // console.log(`--- Tính toán chi tiết cho Ca ${shiftCode} ---`);
                // // console.log(`Ca làm việc: ${shiftStart} - ${shiftEnd} (nghỉ trưa: ${breakStart} - ${breakEnd})`);
                // // console.log(`Thời gian xin nghỉ: ${fromTime} đến ${toTime}`);


                const fromTimeMinutes = timeToMinutes(fromTime);
                const toTimeMinutes = timeToMinutes(toTime);
                const shiftStartMinutes = timeToMinutes(shiftStart);
                const shiftEndMinutes = timeToMinutes(shiftEnd);
                const breakStartMinutes = timeToMinutes(breakStart);
                const breakEndMinutes = timeToMinutes(breakEnd);

                // Debug: Log thời gian để kiểm tra
                console.log('=== TIME CONVERSION DEBUG ===');
                console.log('From time:', fromTime, '→', fromTimeMinutes, 'phút');
                console.log('To time:', toTime, '→', toTimeMinutes, 'phút');
                console.log('From time (hours):', Math.floor(fromTimeMinutes / 60), ':', (fromTimeMinutes % 60).toString().padStart(2, '0'));
                console.log('To time (hours):', Math.floor(toTimeMinutes / 60), ':', (toTimeMinutes % 60).toString().padStart(2, '0'));
                console.log('Is valid (from < to):', fromTimeMinutes < toTimeMinutes);
                console.log('================================');

                // Tính số ngày trong khoảng
                const diffDays = Math.floor((toDate - fromDate) / (24 * 3600 * 1000)) + 1;
                // // console.log(`Số ngày trong khoảng: ${diffDays}`);

                if (diffDays === 1) {
                    // Cùng ngày: tính theo giờ ca làm việc (trừ giờ nghỉ trưa)
                    const workStart = Math.max(fromTimeMinutes, shiftStartMinutes);
                    const workEnd = Math.min(toTimeMinutes, shiftEndMinutes);

                    // // console.log(`Ngày ${fromDate.toLocaleDateString('vi-VN')}: Cùng ngày`);
                    // // console.log(`Thời gian làm việc: ${Math.floor(workStart/60)}:${(workStart%60).toString().padStart(2,'0')} - ${Math.floor(workEnd/60)}:${(workEnd%60).toString().padStart(2,'0')}`);

                    if (workStart >= workEnd) {
                        // // console.log('Không có thời gian làm việc');
                        return 0; // Không có thời gian làm việc
                    }

                    let workMinutes = workEnd - workStart;
                    // // console.log(`Tổng phút làm việc (trước khi trừ nghỉ): ${workMinutes} phút`);

                    // Trừ giờ nghỉ trưa nếu có giao với khoảng thời gian làm việc
                    if (workStart < breakEndMinutes && workEnd > breakStartMinutes) {
                        const breakStartInWork = Math.max(workStart, breakStartMinutes);
                        const breakEndInWork = Math.min(workEnd, breakEndMinutes);
                        if (breakStartInWork < breakEndInWork) {
                            const breakMinutes = breakEndInWork - breakStartInWork;
                            workMinutes -= breakMinutes;
                            // // console.log(`Trừ giờ nghỉ trưa: ${breakMinutes} phút`);
                        }
                    }

                    const workHours = workMinutes / 60;
                    // Logic tính theo thời gian làm việc thực tế (trừ giờ nghỉ)
                    // 1 ngày = 8 tiếng làm việc, 0.5 ngày = 4 tiếng làm việc
                    const days = Math.round((workHours / 8) * 2) / 2; // Làm tròn đến 0.5

                    // // console.log(`Sau khi trừ nghỉ: ${workMinutes} phút = ${workHours.toFixed(2)} giờ`);
                    // // console.log(`Chuyển đổi thành ngày: ${workHours.toFixed(2)} giờ ÷ 8 = ${days} ngày (1 ngày = 8h làm việc)`);

                    return days;
                } else {
                    // Nhiều ngày: tính từng ngày
                    let totalDays = 0;
                    // // console.log(`Nhiều ngày: ${diffDays} ngày`);

                    for (let i = 0; i < diffDays; i++) {
                        const currentDate = new Date(fromDate);
                        currentDate.setDate(fromDate.getDate() + i);

                        if (i === 0) {
                            // Ngày đầu: từ fromTime đến cuối ca (17:00)
                            const workStart = Math.max(fromTimeMinutes, shiftStartMinutes);
                            const workEnd = shiftEndMinutes; // 17:00 = 1020 phút

                            // console.log(`Ngày ${i+1} (${currentDate.toLocaleDateString('vi-VN')}): Ngày đầu`);
                            // console.log(`Thời gian làm việc: ${Math.floor(workStart/60)}:${(workStart%60).toString().padStart(2,'0')} - ${Math.floor(workEnd/60)}:${(workEnd%60).toString().padStart(2,'0')}`);

                            if (workStart < workEnd) {
                                let workMinutes = workEnd - workStart;
                                // // console.log(`Tổng phút làm việc (trước khi trừ nghỉ): ${workMinutes} phút`);

                                // Trừ giờ nghỉ trưa (12:00-13:00) nếu có giao với khoảng thời gian làm việc
                                if (workStart < breakEndMinutes && workEnd > breakStartMinutes) {
                                    const breakStartInWork = Math.max(workStart, breakStartMinutes);
                                    const breakEndInWork = Math.min(workEnd, breakEndMinutes);
                                    if (breakStartInWork < breakEndInWork) {
                                        const breakMinutes = breakEndInWork - breakStartInWork;
                                        workMinutes -= breakMinutes;
                                        // // console.log(`Trừ giờ nghỉ trưa: ${breakMinutes} phút`);
                                    }
                                }

                                const workHours = workMinutes / 60;
                                const dayDays = Math.round((workHours / 8) * 2) / 2;
                                totalDays += dayDays;

                                // console.log(`Sau khi trừ nghỉ: ${workMinutes} phút = ${workHours.toFixed(2)} giờ`);
                                // console.log(`Chuyển đổi thành ngày: ${workHours.toFixed(2)} giờ ÷ 8 = ${dayDays} ngày`);
                            } else {
                                // // console.log('Không có thời gian làm việc');
                            }
                        } else if (i === diffDays - 1) {
                            // Ngày cuối: từ đầu ca (08:00) đến toTime
                            const workStart = shiftStartMinutes; // 08:00 = 480 phút
                            let workEnd;

                            // Xử lý trường hợp toTime là 12:00 AM (00:00) - nghĩa là không có thời gian làm việc ngày cuối
                            if (toTimeMinutes === 0) {
                                workEnd = 0; // Không có thời gian làm việc
                            } else {
                                // 12:00 PM = 720 phút, 17:00 = 1020 phút
                                workEnd = Math.min(toTimeMinutes, shiftEndMinutes);
                            }

                            // console.log(`toTimeMinutes: ${toTimeMinutes}, shiftEndMinutes: ${shiftEndMinutes}, workEnd: ${workEnd}`);

                            // console.log(`Ngày ${i+1} (${currentDate.toLocaleDateString('vi-VN')}): Ngày cuối`);
                            // console.log(`Thời gian làm việc: ${Math.floor(workStart/60)}:${(workStart%60).toString().padStart(2,'0')} - ${Math.floor(workEnd/60)}:${(workEnd%60).toString().padStart(2,'0')}`);

                            if (workStart < workEnd) {
                                let workMinutes = workEnd - workStart;
                                // // console.log(`Tổng phút làm việc (trước khi trừ nghỉ): ${workMinutes} phút`);

                                // Trừ giờ nghỉ trưa (12:00-13:00) nếu có giao với khoảng thời gian làm việc
                                if (workStart < breakEndMinutes && workEnd > breakStartMinutes) {
                                    const breakStartInWork = Math.max(workStart, breakStartMinutes);
                                    const breakEndInWork = Math.min(workEnd, breakEndMinutes);
                                    if (breakStartInWork < breakEndInWork) {
                                        const breakMinutes = breakEndInWork - breakStartInWork;
                                        workMinutes -= breakMinutes;
                                        // // console.log(`Trừ giờ nghỉ trưa: ${breakMinutes} phút`);
                                    }
                                }

                                const workHours = workMinutes / 60;
                                const dayDays = Math.round((workHours / 8) * 2) / 2;
                                totalDays += dayDays;

                                // console.log(`Sau khi trừ nghỉ: ${workMinutes} phút = ${workHours.toFixed(2)} giờ`);
                                // console.log(`Chuyển đổi thành ngày: ${workHours.toFixed(2)} giờ ÷ 8 = ${dayDays} ngày`);
                            } else {
                                // // console.log('Không có thời gian làm việc');
                            }
                        } else {
                            // Ngày giữa: nguyên ngày (8 giờ làm việc, trừ 1 giờ nghỉ = 7 giờ)
                            // console.log(`Ngày ${i+1} (${currentDate.toLocaleDateString('vi-VN')}): Ngày giữa (nguyên ngày)`);
                            // console.log(`Thời gian làm việc: ${shiftStart} - ${shiftEnd} (trừ nghỉ trưa ${breakStart} - ${breakEnd})`);
                            // console.log(`Tính toán: 8 giờ - 1 giờ nghỉ = 7 giờ = 1.0 ngày`);
                            totalDays += 1.0; // Nguyên ngày = 1.0 ngày
                        }
                    }

                    // console.log(`Tổng cộng: ${totalDays} ngày`);
                    return totalDays;
                }

                // Expose hàm ra global để các script khác (submit handler cuối file) cũng dùng được
                window.calculateActualLeaveDays = calculateActualLeaveDays;
            }

            // Khởi tạo lần đầu
            enforceDateRange(false);
            updateTotalDays();

            // Khởi tạo form mode khi trang load
            const requestType = document.getElementById('requestTypeSelect').value;
            window.updateFormMode(requestType);

            // Kiểm tra nếu đây là form sửa và là đi trễ/về sớm
            const requestTypeInput = document.getElementById('requestType');
            if (requestTypeInput && requestTypeInput.value === 'late_early') {
                // Đây là form sửa đi trễ/về sớm, cần ẩn các trường không cần thiết
                window.updateFormMode('late_early');
            }
        });

        // File preview function
        function previewFiles(input) {
            const preview = document.getElementById('file-preview');
            const fileList = document.getElementById('file-list');

            if (input.files.length > 0) {
                preview.style.display = 'block';
                fileList.innerHTML = '';

                Array.from(input.files).forEach((file, index) => {
                    const fileItem = document.createElement('div');
                    fileItem.className = 'list-group-item d-flex justify-content-between align-items-center';

                    const fileInfo = document.createElement('div');
                    fileInfo.innerHTML = `
                        <i class="fas fa-file me-2"></i>
                        <strong>${file.name}</strong>
                        <small class="text-muted ms-2">(${(file.size / 1024 / 1024).toFixed(2)} MB)</small>
                    `;

                    const removeBtn = document.createElement('button');
                    removeBtn.type = 'button';
                    removeBtn.className = 'btn btn-sm btn-outline-danger';
                    removeBtn.innerHTML = '<i class="fas fa-times"></i>';
                    removeBtn.onclick = function () {
                        removeFile(input, index);
                    };

                    fileItem.appendChild(fileInfo);
                    fileItem.appendChild(removeBtn);
                    fileList.appendChild(fileItem);
                });
            } else {
                preview.style.display = 'none';
            }
        }

        // Remove file function
        function removeFile(input, index) {
            const dt = new DataTransfer();
            Array.from(input.files).forEach((file, i) => {
                if (i !== index) {
                    dt.items.add(file);
                }
            });
            input.files = dt.files;
            previewFiles(input);
        }



        // Form validation - moved to DOMContentLoaded event listener
        /*
        document.getElementById('leaveRequestForm').addEventListener('submit', function(e) {
            // console.log('[DEBUG] Form submit event triggered');
            // Ngăn chặn submit mặc định để hiển thị popup xác nhận
            e.preventDefault();
            
            const requiredFields = ['employee_name', 'team', 'employee_code', 'leave_reason', 'leave_from_date', 'leave_from_time', 'leave_to_date', 'leave_to_time', 'leave_shift_code'];
            
            for (let field of requiredFields) {
                if (!document.getElementById(field).value) {
                    // console.log('[DEBUG] Validation failed for field:', field);
                    showToast('Vui lòng điền đầy đủ thông tin bắt buộc', 'error');
                    document.getElementById(field).focus();
                    return;
                }
            }
            // console.log('[DEBUG] Required fields validation passed');

            // Thông tin người thay thế (không bắt buộc): không chặn submit nếu trống
            
            // Validate date range
            const fromDate = new Date(document.getElementById('leave_from_date').value);
            const toDate = new Date(document.getElementById('leave_to_date').value);
            
            if (fromDate > toDate) {
                // console.log('[DEBUG] Date validation failed: fromDate > toDate');
                showToast('Ngày bắt đầu không được lớn hơn ngày kết thúc', 'error');
                document.getElementById('leave_from_date').focus();
                return;
            }
            // console.log('[DEBUG] Date validation passed');

            // Tính toán chính xác khoảng thời gian sử dụng phép (chỉ cho nghỉ phép)
            const requestType = document.getElementById('requestTypeSelect').value;
            if (requestType === 'leave') {
            const parseNum = (v) => parseFloat(v || '0') || 0;
            const totalRequested = parseNum(document.getElementById('annual_leave_days').value)
                                  + parseNum(document.getElementById('unpaid_leave_days').value)
                                  + parseNum(document.getElementById('special_leave_days').value);
            
            // Lấy thông tin ca làm việc
            const shiftCode = document.getElementById('leave_shift_code').value;
            let fromTime = document.getElementById('leave_from_time').value;
            let toTime = document.getElementById('leave_to_time').value;
            
            // Normalize thời gian để xử lý đúng định dạng SA/CH/AM/PM
            fromTime = normalizeTimeFormat(fromTime);
            toTime = normalizeTimeFormat(toTime);
            
            // Tính toán khoảng thời gian thực tế sử dụng phép (theo ca làm việc)
            const actualLeaveDays = shiftCode ? window.calculateActualLeaveDays(fromDate, toDate, fromTime, toTime, shiftCode) : 0;
            
            // Gửi kết quả tính toán lên server
            let calculatedDaysInput = document.getElementById('calculated_leave_days');
            if (!calculatedDaysInput) {
                calculatedDaysInput = document.createElement('input');
                calculatedDaysInput.type = 'hidden';
                calculatedDaysInput.name = 'calculated_leave_days';
                calculatedDaysInput.id = 'calculated_leave_days';
                document.getElementById('leaveRequestForm').appendChild(calculatedDaysInput);
            }
            calculatedDaysInput.value = actualLeaveDays;
            
            // Log chi tiết tính toán
            // console.log('=== TÍNH TOÁN ĐƠN NGHỈ PHÉP ===');
            // console.log(`Khoảng thời gian: ${fromDate.toLocaleDateString('vi-VN')} ${fromTime} đến ${toDate.toLocaleDateString('vi-VN')} ${toTime}`);
            // console.log(`Ca làm việc: Ca ${shiftCode} (${document.getElementById('leave_shift_code').selectedOptions[0].text})`);
            // console.log(`Khoảng thời gian thực tế sử dụng phép: ${actualLeaveDays} ngày`);
            // console.log(`Tổng số ngày xin nghỉ: ${totalRequested} ngày`);
            // console.log(`Phân bổ: Phép năm ${parseNum(document.getElementById('annual_leave_days').value)} + Nghỉ không lương ${parseNum(document.getElementById('unpaid_leave_days').value)} + Nghỉ đặc biệt ${parseNum(document.getElementById('special_leave_days').value)}`);
            // console.log('================================');
            
            // Kiểm tra tổng số ngày xin nghỉ phải lớn hơn 0
            if (totalRequested <= 0) {
                e.preventDefault();
                showToast('Tổng số ngày xin nghỉ phải lớn hơn 0', 'error');
                return;
            }
            
            // Kiểm tra tổng số ngày xin nghỉ phải bằng chính xác khoảng thời gian thực tế
            if (totalRequested !== actualLeaveDays) {
                if (totalRequested > actualLeaveDays) {
                    showToast(`Bạn đã xin quá nhiều! Cần giảm xuống còn ${actualLeaveDays} ngày để gửi đơn.`, 'error');
                } else {
                    showToast(`Bạn chưa xin đủ! Cần thêm ${actualLeaveDays - totalRequested} ngày nữa để gửi đơn.`, 'error');
                }
                return;
            }
            
            // Kiểm tra số ngày xin nghỉ phải là bội số của 0.5
            if (totalRequested % 0.5 !== 0) {
                showToast('Tổng số ngày xin nghỉ phải là bội số của 0.5 (0.5, 1.0, 1.5, 2.0, ...)', 'error');
                return;
            }
            
            // Kiểm tra ít nhất phải có 1 loại nghỉ phép được chọn
            if (totalRequested === 0) {
                showToast('Vui lòng chọn ít nhất một loại nghỉ phép (phép năm, nghỉ không lương, hoặc nghỉ đặc biệt)', 'error');
                return;
            }
            
            // Validate file size
            const fileInput = document.getElementById('attachments');
            if (fileInput.files.length > 0) {
                for (let file of fileInput.files) {
                    if (file.size > 10 * 1024 * 1024) { // 10MB
                        e.preventDefault();
                        showToast(`File "${file.name}" vượt quá kích thước cho phép (10MB)`, 'error');
                        return;
                    }
                }
            }
            
            // Validate half-day multiples (chỉ cho nghỉ phép)
            if (!isLateEarly) {
            const fields = ['annual_leave_days','unpaid_leave_days','special_leave_days'];
            for (let id of fields) {
                const v = document.getElementById(id).value;
                if (v && !((parseFloat(v) * 2) % 1 === 0)) {
                    showToast('Số ngày nghỉ phải là bội số của 0.5 (ví dụ 0.5, 1, 1.5)', 'error');
                    document.getElementById(id).focus();
                    return;
                    }
                }
            }
            
            // Đóng ngoặc cho validation nghỉ phép
            }
            
            // Hiển thị popup xác nhận gửi email
            // console.log('[DEBUG] About to show email confirmation dialog');
            showEmailConfirmationDialog();
        });
        */

        // Hàm hiển thị popup xác nhận gửi email
        function showEmailConfirmationDialog() {
            // console.log('[DEBUG] showEmailConfirmationDialog called');
            // console.log('[DEBUG] Swal available:', typeof Swal);
            Swal.fire({
                title: '📧 Xác nhận gửi email thông báo',
                html: `
                    <div class="text-center">
                        <i class="fas fa-envelope text-primary mb-3" style="font-size: 3rem;"></i>
                        <p class="mb-3">Bạn có muốn gửi email thông báo đơn nghỉ phép này đến phòng nhân sự không?</p>
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            <strong>Lưu ý:</strong> Email sẽ được gửi đến <code>dmihue-nhansu01@acraft.jp</code>
                        </div>
                    </div>
                `,
                icon: 'question',
                showCancelButton: true,
                confirmButtonColor: '#28a745',
                cancelButtonColor: '#6c757d',
                confirmButtonText: '<i class="fas fa-paper-plane me-1"></i> Có, gửi email',
                cancelButtonText: '<i class="fas fa-times me-1"></i> Không gửi email',
                reverseButtons: true,
                customClass: {
                    popup: 'swal2-popup-custom',
                    confirmButton: 'btn btn-success',
                    cancelButton: 'btn btn-secondary'
                },
                buttonsStyling: false
            }).then((result) => {
                if (result.isConfirmed) {
                    // Người dùng đồng ý gửi email
                    submitFormWithEmail(true);
                } else {
                    // Người dùng không muốn gửi email
                    submitFormWithEmail(false);
                }
            });
        }

        // Hàm submit form với hoặc không có email
        function submitFormWithEmail(sendEmail) {
            // console.log('[DEBUG] submitFormWithEmail called with sendEmail:', sendEmail);

            // Xóa input cũ nếu có
            let oldInput = document.getElementById('email_consent');
            if (oldInput) {
                oldInput.remove();
            }

            // Thêm hidden input để báo cho server biết có gửi email hay không
            let emailConsentInput = document.createElement('input');
            emailConsentInput.type = 'hidden';
            emailConsentInput.name = 'email_consent';
            emailConsentInput.id = 'email_consent';
            emailConsentInput.value = sendEmail ? 'yes' : 'no';
            document.getElementById('leaveRequestForm').appendChild(emailConsentInput);

            // console.log('[DEBUG] Created email_consent input with value:', emailConsentInput.value);
            // console.log('[DEBUG] Form action:', document.getElementById('leaveRequestForm').action);

            // Hiển thị thông báo
            if (sendEmail) {
                showToast('Đang gửi đơn nghỉ phép và email thông báo...', 'info');
            } else {
                showToast('Đang gửi đơn nghỉ phép (không gửi email)...', 'info');
            }

            // Submit form
            document.getElementById('leaveRequestForm').submit();
        }

        // Hàm hiển thị Toast (sử dụng SweetAlert2 giống dashboard)
        function showToast(message, type = 'success') {
            // console.log('Showing toast:', message, type);  // Debug log
            const Toast = Swal.mixin({
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 3000,
                timerProgressBar: true,
                didOpen: (toast) => {
                    toast.addEventListener('mouseenter', Swal.stopTimer)
                    toast.addEventListener('mouseleave', Swal.resumeTimer)
                }
            });

            let icon = type;
            if (type === 'success') icon = 'success';
            else if (type === 'error') icon = 'error';
            else if (type === 'warning') icon = 'warning';
            else if (type === 'info') icon = 'info';

            Toast.fire({
                icon: icon,
                title: message
            });
        }


        // Fallback global normalizeTimeFormat để dùng trong submit handler (khi hàm local không sẵn có trong scope)
        if (typeof normalizeTimeFormat !== 'function') {
            function normalizeTimeFormat(timeStr) {
                if (!timeStr) return '00:00';
                if (timeStr.includes('12:00')) {
                    if (/SA/i.test(timeStr)) return '12:00';
                    if (/CH/i.test(timeStr)) return '12:00';
                    if (/PM/i.test(timeStr)) return '12:00';
                    if (/AM/i.test(timeStr)) return '00:00';
                }
                return timeStr.replace(/\s*(SA|CH|AM|PM)\s*/gi, '').trim();
            }
        }

        // Fallback global calculateActualLeaveDays để dùng trong submit handler nếu chưa có
        if (typeof window.calculateActualLeaveDays !== 'function') {
            function _timeToMinutesGlobal(timeStr) {
                if (!timeStr) return 0;
                let clean = String(timeStr).replace(/\s*(SA|CH|AM|PM)\s*/gi, '').trim();
                const [hStr, mStr] = clean.split(':');
                const h = parseInt(hStr || '0', 10);
                const m = parseInt(mStr || '0', 10);
                return (isNaN(h) ? 0 : h) * 60 + (isNaN(m) ? 0 : m);
            }

            window.calculateActualLeaveDays = function (fromDate, toDate, fromTime, toTime, shiftCode) {
                const shiftMap = {
                    '1': { start: '07:30', end: '16:30', breakStart: '11:30', breakEnd: '12:30' },
                    '2': { start: '09:00', end: '18:00', breakStart: '13:00', breakEnd: '14:00' },
                    '3': { start: '11:00', end: '20:00', breakStart: '15:00', breakEnd: '16:00' },
                    '4': { start: '08:00', end: '17:00', breakStart: '12:00', breakEnd: '13:00' }
                };
                const shift = shiftMap[shiftCode] || shiftMap['1'];
                const fromMinutes = _timeToMinutesGlobal(fromTime);
                const toMinutes = _timeToMinutesGlobal(toTime);
                const startShift = _timeToMinutesGlobal(shift.start);
                const endShift = _timeToMinutesGlobal(shift.end);
                const breakStart = _timeToMinutesGlobal(shift.breakStart);
                const breakEnd = _timeToMinutesGlobal(shift.breakEnd);

                const diffDays = Math.floor((toDate - fromDate) / (24 * 3600 * 1000)) + 1;
                if (diffDays <= 0) return 0;

                const calcOneDay = (workStart, workEnd) => {
                    if (workStart >= workEnd) return 0;
                    let workMinutes = workEnd - workStart;
                    if (workStart < breakEnd && workEnd > breakStart) {
                        const bs = Math.max(workStart, breakStart);
                        const be = Math.min(workEnd, breakEnd);
                        if (bs < be) workMinutes -= (be - bs);
                    }
                    const hours = workMinutes / 60;
                    return Math.round((hours / 8) * 2) / 2;
                };

                if (diffDays === 1) {
                    const ws = Math.max(fromMinutes, startShift);
                    const we = Math.min(toMinutes, endShift);
                    return calcOneDay(ws, we);
                }

                let total = 0;
                for (let i = 0; i < diffDays; i++) {
                    if (i === 0) {
                        const ws = Math.max(fromMinutes, startShift);
                        const we = endShift;
                        total += calcOneDay(ws, we);
                    } else if (i === diffDays - 1) {
                        const ws = startShift;
                        const we = Math.min(toMinutes || endShift, endShift);
                        total += calcOneDay(ws, we);
                    } else {
                        total += 1.0;
                    }
                }
                return total;
            };
        }

        // Hiển thị loading khi nộp/sửa đơn, đồng thời reset guard để cho phép hiện toast success mới
        document.addEventListener('DOMContentLoaded', function () {
            try {
                const candidateForms = Array.from(document.querySelectorAll('form'))
                    .filter(f => (f.getAttribute('action') || '').includes('/leave-request'));
                candidateForms.forEach(form => {
                    form.addEventListener('submit', function (e) {
                        // Ngăn chặn submit mặc định để xử lý qua popup
                        e.preventDefault();

                        // console.log('[DEBUG] Form submit event triggered (DOMContentLoaded)');

                        // Validation tổng quát - kiểm tra tất cả lỗi có thể xảy ra
                        const validationResult = validateAllFields();

                        if (validationResult.hasErrors) {
                            // Hiển thị tất cả lỗi
                            const errorMessage = validationResult.errorMessages.join('\n• ');
                            showToast(`❌ Có lỗi trong form:\n• ${errorMessage}`, 'error');

                            // Focus vào field đầu tiên có lỗi
                            const firstErrorField = document.querySelector('.is-invalid');
                            if (firstErrorField) {
                                firstErrorField.focus();
                            }
                            return;
                        }

                        // Nếu không có lỗi, tiếp tục với việc tính toán và gửi form (chỉ cho nghỉ phép)
                        const requestType = document.getElementById('requestTypeSelect').value;
                        if (requestType === 'leave') {
                            const parseNum = (v) => parseFloat(v || '0') || 0;
                            const totalRequested = parseNum(document.getElementById('annual_leave_days').value)
                                + parseNum(document.getElementById('unpaid_leave_days').value)
                                + parseNum(document.getElementById('special_leave_days').value);

                            // Lấy thông tin ca làm việc
                            const shiftCode = document.getElementById('leave_shift_code').value;
                            let fromTime = document.getElementById('leave_from_time').value;
                            let toTime = document.getElementById('leave_to_time').value;

                            // Normalize thời gian để xử lý đúng định dạng SA/CH/AM/PM
                            fromTime = normalizeTimeFormat(fromTime);
                            toTime = normalizeTimeFormat(toTime);

                            // Tính toán khoảng thời gian thực tế sử dụng phép (theo ca làm việc)
                            const fromDate = new Date(document.getElementById('leave_from_date').value);
                            const toDate = new Date(document.getElementById('leave_to_date').value);
                            const actualLeaveDays = window.calculateActualLeaveDays(fromDate, toDate, fromTime, toTime, shiftCode);

                            // Gửi kết quả tính toán lên server
                            let calculatedDaysInput = document.getElementById('calculated_leave_days');
                            if (!calculatedDaysInput) {
                                calculatedDaysInput = document.createElement('input');
                                calculatedDaysInput.type = 'hidden';
                                calculatedDaysInput.name = 'calculated_leave_days';
                                calculatedDaysInput.id = 'calculated_leave_days';
                                document.getElementById('leaveRequestForm').appendChild(calculatedDaysInput);
                            }
                            calculatedDaysInput.value = actualLeaveDays;

                            // Cho phép hiển thị lại toast success cho request mới
                            try { localStorage.removeItem('email_status_shown_request_id'); } catch (e) { }

                            // Gọi popup xác nhận email thay vì submit trực tiếp
                            // console.log('[DEBUG] About to show email confirmation dialog');
                            showEmailConfirmationDialog();
                        } else {
                            // Cho đi trễ/về sớm, submit trực tiếp không cần validation số ngày nghỉ
                            showEmailConfirmationDialog();
                        }
                    }, { once: true });
                });
            } catch (_) { }
        });
