/**
 * Role Switch Optimizer - Real-time updates and cache management
 */
class RoleSwitchOptimizer {
    constructor() {
        this.activeRequests = new Map();
        this.roleSwitchQueue = [];
        this.isProcessing = false;
        this.lastRoleSwitch = 0;
        this.cache = new Map();
        this.cacheTimeout = 5000; // 5 seconds cache
        this.minSwitchInterval = 1000; // Minimum 1 second between role switches (optimized)
        this.lastSuccessfulSwitch = 0;
        this.switchCooldown = false;
        this.uiUpdateDelay = 200; // Delay for smooth UI transitions
    }

    /**
     * Optimized role switching with debouncing and cache invalidation
     */
    async switchRole(newRole) {
        const now = Date.now();
        this.lastRoleSwitch = now;

        // Check cooldown period
        const timeSinceLastSwitch = now - this.lastSuccessfulSwitch;
        if (timeSinceLastSwitch < this.minSwitchInterval) {
            const remainingTime = Math.ceil((this.minSwitchInterval - timeSinceLastSwitch) / 1000);
            this.showWarning(`Vui lòng đợi ${remainingTime} giây trước khi chuyển vai trò tiếp theo`);

            // Queue the role switch for later (avoid duplicates)
            if (!this.roleSwitchQueue.includes(newRole)) {
                this.roleSwitchQueue.push(newRole);
            }
            setTimeout(() => {
                if (this.roleSwitchQueue.length > 0) {
                    const queuedRole = this.roleSwitchQueue.shift();
                    this.switchRole(queuedRole);
                }
            }, this.minSwitchInterval - timeSinceLastSwitch);
            return;
        }

        // Prevent rapid switching during cooldown
        if (this.switchCooldown) {
            this.showWarning('Đang xử lý chuyển vai trò, vui lòng đợi...');
            return;
        }

        // Cancel all pending requests for current role
        this.cancelAllPendingRequests();

        // Clear cache for new role
        this.clearCacheForRole(newRole);

        // Debounce rapid role switches (avoid duplicates in queue)
        if (this.isProcessing) {
            if (!this.roleSwitchQueue.includes(newRole)) {
                this.roleSwitchQueue.push(newRole);
            }
            return;
        }

        this.isProcessing = true;
        this.switchCooldown = true;

        try {

            
            // Update server-side role and get message
            const message = await this.updateServerRole(newRole);
            
            // Update UI immediately for responsive feel
            this.updateUIForRole(newRole);
            
            // Small delay for smooth UI transition
            await new Promise(resolve => setTimeout(resolve, this.uiUpdateDelay));
            
            // Load data in parallel with cache optimization
            await this.loadRoleDataParallel(newRole);
            
            // Record successful switch
            this.lastSuccessfulSwitch = Date.now();
            
            // Hiển thị duy nhất một thông báo thành công
            this.showSuccess(message || `Đã chuyển sang vai trò ${this.getRoleDisplayName(newRole)}`);
            
        } catch (error) {
            console.error('Role switch error:', error);
            this.showError('Lỗi khi chuyển vai trò');
        } finally {
            this.isProcessing = false;
            
            // Set cooldown period
            setTimeout(() => {
                this.switchCooldown = false;
            }, this.minSwitchInterval);
            
            // Process queued role switches after cooldown
            if (this.roleSwitchQueue.length > 0) {
                setTimeout(() => {
                    if (this.roleSwitchQueue.length > 0 && !this.switchCooldown) {
                        const nextRole = this.roleSwitchQueue.shift();
                        this.switchRole(nextRole);
                    }
                }, this.minSwitchInterval);
            }
        }
    }

    /**
     * Update server role with proper error handling
     */
    async updateServerRole(role) {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
        
        const controller = new AbortController();
        this.activeRequests.set('role-switch', controller);
        
        const response = await fetch('/switch-role', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ role }),
            signal: controller.signal
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Trả về message để caller quyết định hiển thị toast (tránh hiển thị 2 lần)
        return data.message || 'Đã chuyển vai trò thành công';
    }

    /**
     * Load role data in parallel with cache optimization
     */
    async loadRoleDataParallel(role) {
        const promises = [];
        
        // Show smooth loading indicator
        const approvalSection = document.getElementById('approvalSection');
        if (approvalSection && typeof window.smoothTransitions !== 'undefined') {
            window.smoothTransitions.showProgress(approvalSection, 800);
        }
        
        // Always load approval data for management roles
        if (['TEAM_LEADER', 'MANAGER', 'ADMIN'].includes(role)) {
            promises.push(this.loadApprovalDataOptimized(role));
            promises.push(this.loadPendingLeaveCount());
        }
        
        // Load attendance history for employees
        if (role === 'EMPLOYEE') {
            promises.push(this.loadAttendanceHistoryOptimized());
        }
        
        // Load all attendance data for admins
        if (role === 'ADMIN') {
            promises.push(this.loadAllAttendanceDataOptimized());
        }
        
        // Execute all promises in parallel
        await Promise.allSettled(promises);
    }

    /**
     * Optimized approval data loading with cache
     */
    async loadApprovalDataOptimized(role) {
        const cacheKey = `approval-${role}`;
        const cached = this.getCachedData(cacheKey);
        
        // Force refresh for role switches to ensure fresh data
        if (cached && this.lastSuccessfulSwitch === 0) {
            this.updateApprovalUI(cached);
            return;
        }
        
        const controller = new AbortController();
        this.activeRequests.set('approval', controller);
        
        try {
            // Add timestamp and force refresh parameters
            const url = `/api/attendance/pending?t=${Date.now()}&force_refresh=1&role=${role}`;
            const response = await fetch(url, {
                signal: controller.signal,
                headers: {
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            // Only cache if data is fresh
            if (data.freshness && data.freshness.needs_refresh === false) {
                this.setCachedData(cacheKey, data);
            }
            
            this.updateApprovalUI(data);
            
        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error('Error loading approval data:', error);
                this.showError('Lỗi khi tải dữ liệu phê duyệt');
            }
        }
    }

    /**
     * Optimized attendance history loading
     */
    async loadAttendanceHistoryOptimized() {
        const cacheKey = 'attendance-history';
        const cached = this.getCachedData(cacheKey);
        
        if (cached) {
            this.updateAttendanceHistoryUI(cached);
            return;
        }
        
        const controller = new AbortController();
        this.activeRequests.set('history', controller);
        
        try {
            const response = await fetch(`/api/attendance/history?t=${Date.now()}`, {
                signal: controller.signal,
                headers: {
                    'Cache-Control': 'no-cache, no-store, must-revalidate'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            this.setCachedData(cacheKey, data);
            this.updateAttendanceHistoryUI(data);
            
        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error('Error loading attendance history:', error);
            }
        }
    }

    /**
     * Optimized all attendance data loading for admin
     */
    async loadAllAttendanceDataOptimized() {
        const cacheKey = 'all-attendance';
        const cached = this.getCachedData(cacheKey);
        
        if (cached) {
            this.updateAllAttendanceUI(cached);
            return;
        }
        
        const controller = new AbortController();
        this.activeRequests.set('all-attendance', controller);
        
        try {
            const response = await fetch(`/api/attendance/history?all=1&t=${Date.now()}`, {
                signal: controller.signal,
                headers: {
                    'Cache-Control': 'no-cache, no-store, must-revalidate'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            this.setCachedData(cacheKey, data);
            this.updateAllAttendanceUI(data);
            
        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error('Error loading all attendance data:', error);
            }
        }
    }

    /**
     * Cache management
     */
    getCachedData(key) {
        const cached = this.cache.get(key);
        if (cached && (Date.now() - cached.timestamp) < this.cacheTimeout) {
            return cached.data;
        }
        return null;
    }

    setCachedData(key, data) {
        this.cache.set(key, {
            data: data,
            timestamp: Date.now()
        });
    }

    clearCacheForRole(role) {
        // Clear role-specific cache
        const keysToDelete = [];
        for (const key of this.cache.keys()) {
            if (key.includes(role) || key.includes('approval') || key.includes('attendance')) {
                keysToDelete.push(key);
            }
        }
        keysToDelete.forEach(key => this.cache.delete(key));
    }

    /**
     * Cancel all pending requests
     */
    cancelAllPendingRequests() {
        for (const [key, controller] of this.activeRequests) {
            controller.abort();
        }
        this.activeRequests.clear();
    }

    /**
     * UI update methods
     */
    updateUIForRole(role) {
        // Use existing updateUIForRole function
        if (typeof window.updateUIForRole === 'function') {
            window.updateUIForRole(role);
        }
    }

    updateApprovalUI(data) {
        if (typeof window.loadApprovalAttendance === 'function') {
            // Update the approval section directly
            const approvalBody = document.getElementById('approvalAttendanceBody');
            if (approvalBody && data.data) {
                // Trigger the existing loadApprovalAttendance function
                window.loadApprovalAttendance(1);
            }
        }
    }

    updateAttendanceHistoryUI(data) {
        if (typeof window.updateAttendanceHistory === 'function') {
            window.updateAttendanceHistory();
        }
    }

    updateAllAttendanceUI(data) {
        // Update all attendance history for admin
        if (typeof window.loadAllAttendanceHistory === 'function') {
            window.loadAllAttendanceHistory();
        }
    }

    /**
     * Load pending leave count
     */
    async loadPendingLeaveCount() {
        const controller = new AbortController();
        this.activeRequests.set('leave-count', controller);
        
        try {
            const response = await fetch(`/api/leave-requests/pending-count?t=${Date.now()}`, {
                signal: controller.signal,
                headers: {
                    'Cache-Control': 'no-cache, no-store, must-revalidate'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.updatePendingLeaveCountUI(data.count);
            }
        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error('Error loading pending leave count:', error);
            }
        }
    }

    updatePendingLeaveCountUI(count) {
        const badge = document.querySelector('.pending-leave-badge');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline' : 'none';
        }
    }

    /**
     * Notification methods
     */
    showSuccess(message) {
        if (typeof window.showToast === 'function') {
            window.showToast(message, 'success');
        }
    }

    showError(message) {
        if (typeof window.showToast === 'function') {
            window.showToast(message, 'error');
        }
    }

    showWarning(message) {
        if (typeof window.showToast === 'function') {
            window.showToast(message, 'warning', 3000); // 3 seconds for warnings
        } else {
            console.warn(message);
        }
    }

    showLoading(message) {
        if (typeof window.showToast === 'function') {
            window.showToast(message, 'info', 1000); // 1 second for loading
        }
    }

    /**
     * Get role display name
     */
    getRoleDisplayName(role) {
        const roleNames = {
            'EMPLOYEE': 'Nhân viên',
            'TEAM_LEADER': 'Trưởng nhóm',
            'MANAGER': 'Quản lý',
            'ADMIN': 'Quản trị viên'
        };
        return roleNames[role] || role;
    }
}

// Initialize global instance
window.roleSwitchOptimizer = new RoleSwitchOptimizer();

// Override existing switchRole function
window.switchRole = function(role) {
    window.roleSwitchOptimizer.switchRole(role);
};
