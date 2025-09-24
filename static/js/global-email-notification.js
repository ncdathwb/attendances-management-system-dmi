/**
 * Global Email Notification System
 * Hiển thị thông báo email status trên tất cả các trang
 */
// Guard để tránh khởi tạo nhiều lần và cho phép tắt trên một số trang
if (window.__GLOBAL_EMAIL_NOTIF_INITED__ === undefined) {
    window.__GLOBAL_EMAIL_NOTIF_INITED__ = false;
}
console.log('[global-email-notification] script file executing');

// Hàm kiểm tra trạng thái email toàn cục
function checkGlobalEmailStatus() {
    // Kiểm tra request_id từ URL parameters hoặc data attribute
    const urlParams = new URLSearchParams(window.location.search);
    let requestId = urlParams.get('request_id');

    if (!requestId) {
        const bodyElement = document.body;
        if (bodyElement) {
            requestId = bodyElement.getAttribute('data-request-id');
        }
    }

    // Nếu có requestId cụ thể, kiểm tra theo request
    if (requestId) {
        const roleSelect = document.getElementById('role-select');
        const currentRole = window.currentRole || (roleSelect ? roleSelect.value : 'EMPLOYEE');
        console.log('Checking email status for role:', currentRole, 'requestId:', requestId);
        checkEmailStatus(parseInt(requestId));
            return;
        }
        
    // Nếu KHÔNG có requestId, fallback: kiểm tra trạng thái gần nhất từ session
    console.log('No request_id found. Fallback to latest email status');
    checkLatestEmailStatus();
}

// Hàm kiểm tra trạng thái email
function checkEmailStatus(requestId) {
    if (!requestId) return;
    
    let pollCount = 0;
    const maxPolls = 20; // Tối đa 20 lần polling (khoảng 1 phút)
    
    const checkStatus = () => {
        pollCount++;
        console.log(`Polling attempt ${pollCount}/${maxPolls} for request ${requestId}`);
        
        // Dừng polling nếu đã quá số lần cho phép
        if (pollCount > maxPolls) {
            console.log('Max polling attempts reached, stopping');
            return;
        }
        console.log(`Checking email status for request_id: ${requestId}`);
        fetch(`/api/email-status/${requestId}`)
            .then(response => response.json())
            .then(data => {
                console.log('Email status response:', data);
                if (data.status === 'success') {
                    console.log('Email sent successfully, showing toast');
                    showToast('Email đã được gửi thành công đến HR!', 'success');
                    return; // Dừng kiểm tra
                } else if (data.status === 'error') {
                    console.log('Email send failed, showing error toast');
                    showToast('Có lỗi khi gửi email: ' + data.message, 'error');
                    return; // Dừng kiểm tra
                } else if (data.status === 'skipped') {
                    console.log('Email notification skipped for non-employee role');
                    return; // Dừng kiểm tra cho vai trò không phải nhân viên
                } else if (data.status === 'sending') {
                    console.log('Email still sending, checking again in 3 seconds');
                    // Tiếp tục kiểm tra sau 3 giây
                    setTimeout(checkStatus, 3000);
                } else {
                    console.log('Unknown status, checking again in 2 seconds');
                    // Trạng thái unknown, kiểm tra lại sau 2 giây
                    setTimeout(checkStatus, 2000);
                }
            })
            .catch(error => {
                console.error('Error checking email status:', error);
                setTimeout(checkStatus, 3000); // Thử lại sau 3 giây
            });
    };
    
    // Bắt đầu kiểm tra sau 2 giây để đảm bảo email có thời gian gửi
    setTimeout(checkStatus, 2000);
}

// Kiểm tra trạng thái email gần nhất từ session (không cần request_id)
function checkLatestEmailStatus() {
    // Guard: tránh hiện nhiều lần cho cùng request_id (kể cả reload)
    const shownKey = 'email_status_shown_request_id';

    const checkStatus = () => {
        console.log('Checking latest email status');
        fetch('/api/email-status/latest')
            .then(response => response.json())
            .then(data => {
                console.log('Latest email status response:', data);
                if (data.status === 'success') {
                    const alreadyShownFor = localStorage.getItem(shownKey);
                    if (alreadyShownFor !== String(data.request_id)) {
                        console.log('Latest: Email sent successfully, showing toast');
                        showToast('Email đã được gửi thành công đến HR!', 'success');
                        localStorage.setItem(shownKey, String(data.request_id || ''));
                    } else {
                        console.log('Latest: toast already shown for request', data.request_id);
                    }
                    return;
                } else if (data.status === 'error') {
                    const alreadyShownFor = localStorage.getItem(shownKey);
                    if (alreadyShownFor !== String(data.request_id)) {
                        console.log('Latest: Email send failed, showing error toast');
                        showToast('Có lỗi khi gửi email: ' + data.message, 'error');
                        localStorage.setItem(shownKey, String(data.request_id || ''));
                    } else {
                        console.log('Latest: error toast already shown for request', data.request_id);
                    }
                    return;
                } else if (data.status === 'sending') {
                    // Khi phát hiện bắt đầu một lượt gửi mới, xóa guard để lần success tiếp theo hiển thị toast
                    try { localStorage.removeItem(shownKey); } catch (e) {}
                    console.log('Latest: Email still sending, checking again in 3 seconds');
                    setTimeout(checkStatus, 3000);
                } else {
                    // unknown -> dừng im lặng
                    console.log('Latest: Unknown status, stop polling');
                }
            })
            .catch(error => {
                console.error('Error checking latest email status:', error);
                setTimeout(checkStatus, 3000);
            });
    };

    // bắt đầu sau 2s
    setTimeout(checkStatus, 2000);
}

// Đảm bảo các hàm có mặt trên phạm vi global để template có thể kiểm tra
try {
    window.checkGlobalEmailStatus = checkGlobalEmailStatus;
    window.checkEmailStatus = checkEmailStatus;
    window.checkLatestEmailStatus = checkLatestEmailStatus;
    console.log('[global-email-notification] functions exposed to window');
} catch (e) {
    console.error('[global-email-notification] failed to expose functions:', e);
}

// Hàm hiển thị Toast (sử dụng SweetAlert2)
function showToast(message, type = 'success') {
    console.log('Showing toast:', message, type);
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

// Hàm khởi tạo với delay để đợi window.currentRole được set
function initializeEmailNotification() {
    if (window.__GLOBAL_EMAIL_NOTIF_INITED__) {
        console.log('Email notification already initialized, skip');
        return;
    }
    // Cho phép tắt trên một số trang bằng data attribute
    try {
        const disable = document.body && document.body.getAttribute('data-disable-email-status');
        if (disable === '1' || disable === 'true') {
            console.log('Email notification disabled by page flag');
            return;
        }
    } catch (e) {}
    console.log('Initializing email notification...');
    console.log('Current role:', window.currentRole);
    console.log('Request ID from URL:', new URLSearchParams(window.location.search).get('request_id'));
    console.log('Request ID from data attribute:', document.body ? document.body.getAttribute('data-request-id') : 'Body not found');
    
    // Đợi một chút để đảm bảo window.currentRole đã được set
    setTimeout(() => {
        console.log('Checking email status after delay...');
        checkGlobalEmailStatus();
        window.__GLOBAL_EMAIL_NOTIF_INITED__ = true;
    }, 100);
}

// Khởi tạo khi DOM loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Global email notification script loaded');
    // Khởi tạo trễ nhẹ để ưu tiên render UI
    setTimeout(initializeEmailNotification, 300);
    // Khởi tạo overlay chặn thao tác dùng chung cho mọi trang
    try { __initGlobalBlockingOverlay(); } catch (e) { console.warn('init overlay failed', e); }
    // Log mốc thời gian page ready
    try {
        const t0 = (window.performance && performance.timing && performance.timing.navigationStart) ? performance.timing.navigationStart : Date.now();
        console.log(`[perf] DOMContentLoaded at ${Math.round(performance.now ? performance.now() : (Date.now() - t0))} ms`);
    } catch (_) {}
});

// Cũng kiểm tra ngay lập tức nếu DOM đã sẵn sàng
if (document.readyState !== 'loading') {
    console.log('DOM already loaded, scheduling email notification init');
    setTimeout(initializeEmailNotification, 300);
}

// ===================== GLOBAL UI BLOCKING OVERLAY (for all pages) =====================
function __initGlobalBlockingOverlay(){
    if (window.__GLOBAL_OVERLAY_INITED__) return;
    window.__GLOBAL_OVERLAY_INITED__ = true;

    let overlayEl = null;
    let styleEl = null;
    let blockCount = 0;

    function ensureStyle(){
        if (styleEl) return;
        styleEl = document.createElement('style');
        styleEl.type = 'text/css';
        styleEl.textContent = `
        .global-blocking-overlay{position:fixed;inset:0;background:rgba(15,23,42,.45);backdrop-filter:saturate(120%) blur(2px);z-index:2147483000;display:flex;align-items:center;justify-content:center}
        .global-blocking-card{background:#0b1220;color:#e6edf3;border:1px solid rgba(255,255,255,0.08);border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,0.35);padding:16px 20px;display:flex;align-items:center;gap:10px;max-width:90%;}
        .global-blocking-spin{width:20px;height:20px;border-radius:50%;border:3px solid rgba(255,255,255,0.25);border-top-color:#60a5fa;animation:gb_spin .9s linear infinite}
        .global-blocking-text{font-weight:600;letter-spacing:.2px}
        @keyframes gb_spin{to{transform:rotate(360deg)}}
        body.__ui_blocked{pointer-events:none}
        body.__ui_blocked .global-blocking-overlay{pointer-events:auto}
        a[data-no-blocking], form[data-no-blocking]{pointer-events:auto}
        `;
        document.head.appendChild(styleEl);
    }

    function ensureOverlay(){
        if (overlayEl) return overlayEl;
        // Tái sử dụng overlay nếu đã tồn tại do trang khác tạo
        const existing = document.querySelector('.global-blocking-overlay');
        if (existing) {
            overlayEl = existing;
            ensureStyle();
            return overlayEl;
        }
        ensureStyle();
        overlayEl = document.createElement('div');
        overlayEl.className = 'global-blocking-overlay';
        overlayEl.style.display = 'none';
        overlayEl.innerHTML = `
            <div class="global-blocking-card">
                <div class="global-blocking-spin"></div>
                <div class="global-blocking-text">Đang xử lý...</div>
            </div>
        `;
        document.body.appendChild(overlayEl);
        return overlayEl;
    }

    function setMessage(msg){
        const el = overlayEl?.querySelector('.global-blocking-text');
        if (el && msg) el.textContent = msg;
    }

    function showBlocking(msg){
        ensureOverlay();
        setMessage(msg || 'Đang xử lý...');
        blockCount++;
        overlayEl.style.display = 'flex';
        document.body.classList.add('__ui_blocked');
    }

    function hideBlocking(){
        if (blockCount > 0) blockCount--;
        if (blockCount === 0 && overlayEl){
            overlayEl.style.display = 'none';
            document.body.classList.remove('__ui_blocked');
        }
    }

    // Expose nếu chưa có (tránh đè của dashboard.js)
    if (!window.__showBlocking) window.__showBlocking = showBlocking;
    if (!window.__hideBlocking) window.__hideBlocking = hideBlocking;

    // 1) Bật overlay khi click link chuyển trang (same-origin)
    document.addEventListener('click', function(e){
        const a = e.target && (e.target.closest ? e.target.closest('a') : null);
        if (!a) return;
        if (a.getAttribute('data-no-blocking') === '1') return;
        const href = a.getAttribute('href') || '';
        if (!href || href.startsWith('#')) return;
        // Bỏ qua mở tab mới / download
        if (a.getAttribute('target') === '_blank') return;
        if (a.hasAttribute('download')) return;
        // Chỉ same-origin
        try {
            const url = new URL(href, window.location.href);
            if (url.origin !== window.location.origin) return;
        } catch (_) { /* ignore */ }
        const clickStart = (performance && performance.now) ? performance.now() : Date.now();
        a.setAttribute('data-click-start', String(clickStart));
        showBlocking('Đang tải trang...');
        // Auto hide nếu điều hướng bị chặn
        setTimeout(()=>{ hideBlocking(); }, 10000);
    }, true);

    // 2) Bật overlay khi submit form chuyển trang
    document.addEventListener('submit', function(e){
        const form = e.target;
        if (!form || form.getAttribute('data-no-blocking') === '1') return;
        form.setAttribute('data-submit-start', String((performance && performance.now) ? performance.now() : Date.now()));
        showBlocking('Đang gửi...');
        setTimeout(()=>{ hideBlocking(); }, 15000);
    }, true);

    // 3) Hook fetch: mặc định chỉ chặn với method khác GET hoặc khi yêu cầu bật
    try {
        const nativeFetch = window.fetch;
        window.fetch = function(url, options){
            const opts = options || {};
            const method = (opts.method || 'GET').toUpperCase();
            const urlStr = typeof url === 'string' ? url : (url?.url || '');
            const wantBlock = opts.showBlocking === true || method !== 'GET' || urlStr.includes('/switch-role');
            const start = (performance && performance.now) ? performance.now() : Date.now();
            console.log(`[perf] fetch -> ${method} ${urlStr}`);
            if (wantBlock) {
                showBlocking(method === 'GET' ? 'Đang tải...' : 'Đang xử lý...');
            }
            const p = nativeFetch.apply(this, arguments);
            return p.then(async (res)=>{
                const end = (performance && performance.now) ? performance.now() : Date.now();
                console.log(`[perf] fetch <- ${method} ${urlStr} ${res.status} in ${Math.round(end - start)} ms`);
                return res;
            }).catch((err)=>{
                const end = (performance && performance.now) ? performance.now() : Date.now();
                console.log(`[perf] fetch !! ${method} ${urlStr} error in ${Math.round(end - start)} ms`, err);
                throw err;
            }).finally(()=>{ if (wantBlock) setTimeout(hideBlocking, 300); });
        };
    } catch (e) { /* ignore */ }

    // 4) Trạng thái tải trang
    window.addEventListener('beforeunload', function(){
        try {
            // Nếu có mốc click/submit, log thời gian tới beforeunload
            const a = document.querySelector('a[data-click-start]');
            if (a) {
                const start = parseFloat(a.getAttribute('data-click-start') || '0');
                const end = (performance && performance.now) ? performance.now() : Date.now();
                if (start) console.log(`[perf] nav (click -> beforeunload): ${Math.round(end - start)} ms`);
            }
            const form = document.querySelector('form[data-submit-start]');
            if (form) {
                const start = parseFloat(form.getAttribute('data-submit-start') || '0');
                const end = (performance && performance.now) ? performance.now() : Date.now();
                if (start) console.log(`[perf] form submit (submit -> beforeunload): ${Math.round(end - start)} ms`);
            }
            showBlocking('Đang tải trang...');
        } catch (_) {}
    });
}

// ===================== GLOBAL PERF RECORDER (session-wide) =====================
(function __initGlobalPerfRecorder(){
    if (window.__PERF_REC_INITED__) return; window.__PERF_REC_INITED__ = true;
    const hasNow = !!(window.performance && performance.now);
    const now = ()=> hasNow ? performance.now() : Date.now();
    const navStart = (performance && performance.timeOrigin) ? performance.timeOrigin : (performance?.timing?.navigationStart || Date.now());
    const state = {
        enabled: true,
        startedAt: now(),
        events: []
    };
    function add(evt){ if (!state.enabled) return; try{ state.events.push({ t: now(), ...evt }); }catch(_){} }
    function bytesOfBody(body){ try{ if (!body) return 0; if (typeof body === 'string') return new Blob([body]).size; if (body instanceof FormData){ let total=0; for (const [k,v] of body.entries()){ if (typeof v === 'string') total+= new Blob([v]).size; else if (v && v.size) total+= v.size; } return total; } if (body instanceof Blob) return body.size; if (typeof body === 'object') return new Blob([JSON.stringify(body)]).size; return 0; }catch(_){ return 0; } }
    function summary(){
        const total = state.events.length;
        const fetches = state.events.filter(e=> e.type==='fetch');
        const clicks = state.events.filter(e=> e.type==='click');
        const submits = state.events.filter(e=> e.type==='submit');
        const navs = state.events.filter(e=> e.type==='nav');
        const worstFetch = fetches.slice().sort((a,b)=> (b.dur||0)-(a.dur||0))[0];
        return { totalEvents: total, fetchCount: fetches.length, clickCount: clicks.length, submitCount: submits.length, navCount: navs.length, worstFetch: worstFetch ? { url: worstFetch.url, method: worstFetch.method, durMs: Math.round(worstFetch.dur||0), status: worstFetch.status } : null };
    }
    function dump(){ return { startedAt: new Date(navStart).toISOString(), events: state.events, summary: summary() }; }
    function printSummary(){ try{ const s = summary(); console.log('[perf:summary]', s); }catch(_){} }
    window.__perf = {
        add,
        summary,
        dump,
        enable: ()=>{ state.enabled = true; },
        disable: ()=>{ state.enabled = false; },
    };

    // Paint metrics
    try {
        if ('PerformanceObserver' in window) {
            const po = new PerformanceObserver((list)=>{
                list.getEntries().forEach(entry=>{
                    if (entry.name === 'first-paint' || entry.name === 'first-contentful-paint') {
                        add({ type: 'paint', name: entry.name, dur: entry.startTime });
                        console.log(`[perf] ${entry.name}: ${Math.round(entry.startTime)} ms`);
                    }
                });
            });
            po.observe({ type: 'paint', buffered: true });
        }
    } catch(_){}

    // Resource summary on hide
    function logResourceSummary(){
        try{
            const entries = performance?.getEntriesByType ? performance.getEntriesByType('resource') : [];
            if (!entries || !entries.length) return;
            const heavy = entries.filter(e=> (e.duration||0) > 200).sort((a,b)=> b.duration-a.duration).slice(0,5).map(e=> ({ name: e.name, type: e.initiatorType, durMs: Math.round(e.duration||0), size: (e.transferSize||0) }));
            if (heavy.length) console.log('[perf] top resources', heavy);
        } catch(_){}
    }

    document.addEventListener('click', function(e){
        try {
            const a = e.target && (e.target.closest ? e.target.closest('a') : null);
            if (a) {
                add({ type: 'click', text: (a.textContent||'').trim().slice(0,60), href: a.getAttribute('href')||'' });
            }
        } catch(_){}
    }, true);

    document.addEventListener('submit', function(e){
        try { const form = e.target; if (form) add({ type: 'submit', action: form.getAttribute('action')||'', method: (form.getAttribute('method')||'GET').toUpperCase() }); } catch(_){}
    }, true);

    // Hook fetch (augment existing patch if any)
    try {
        const prevFetch = window.fetch;
        window.fetch = function(url, options){
            const opts = options || {};
            const method = (opts.method || 'GET').toUpperCase();
            const urlStr = typeof url === 'string' ? url : (url?.url || '');
            const start = now();
            const bodyBytes = bytesOfBody(opts.body);
            add({ type: 'fetch', phase: 'start', url: urlStr, method, bodyBytes });
            return prevFetch.apply(this, arguments).then(res=>{
                const end = now();
                add({ type: 'fetch', phase: 'end', url: urlStr, method, status: res.status, dur: end - start });
                return res;
            }).catch(err=>{
                const end = now();
                add({ type: 'fetch', phase: 'error', url: urlStr, method, err: String(err), dur: end - start });
                throw err;
            });
        };
    } catch(_){}

    // Navigation measure
    window.addEventListener('beforeunload', function(){ add({ type: 'nav', phase: 'beforeunload' }); printSummary(); logResourceSummary(); });
    document.addEventListener('visibilitychange', function(){ if (document.visibilityState === 'hidden') { add({ type: 'nav', phase: 'hidden' }); printSummary(); logResourceSummary(); } });
    
    // Gửi log về server khi đóng/ẩn tab (sử dụng sendBeacon nếu có)
    async function sendPerfLog(){
        if (window.__PERF_SENT__) return; // tránh gửi nhiều lần
        window.__PERF_SENT__ = true;
        try{
            const payload = JSON.stringify(window.__perf.dump());
            const blob = new Blob([payload], { type: 'application/json' });
            if (navigator.sendBeacon) {
                navigator.sendBeacon('/api/perf-log', blob);
            } else {
                fetch('/api/perf-log', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: payload, keepalive: true });
            }
        }catch(e){ console.warn('send perf log failed', e); }
    }
    window.addEventListener('beforeunload', sendPerfLog, { capture: true });
    document.addEventListener('visibilitychange', function(){ if (document.visibilityState === 'hidden') sendPerfLog(); }, { capture: true });
})();

// ===================== SSE: realtime push (preferred) =====================
function startSSEEmailStatus() {
    if (!('EventSource' in window)) {
        console.log('SSE not supported, fallback to polling');
        return;
    }
    try {
        const es = new EventSource('/sse/email-status');
        es.addEventListener('email_status', (evt) => {
            try {
                const data = JSON.parse(evt.data);
                console.log('SSE email status:', data);
                const shownKey = 'email_status_shown_request_id';
                if (data.status === 'success') {
                    const already = localStorage.getItem(shownKey);
                    if (already !== String(data.request_id)) {
                        showToast('Email đã được gửi thành công đến HR!', 'success');
                        localStorage.setItem(shownKey, String(data.request_id || ''));
                    }
                } else if (data.status === 'error') {
                    const already = localStorage.getItem(shownKey);
                    if (already !== String(data.request_id)) {
                        showToast('Có lỗi khi gửi email: ' + (data.message || ''), 'error');
                        localStorage.setItem(shownKey, String(data.request_id || ''));
                    }
                } else if (data.status === 'sending') {
                    try { localStorage.removeItem(shownKey); } catch (e) {}
                }
            } catch (e) {
                console.error('SSE parse error', e);
            }
        });
        es.onerror = () => {
            console.log('SSE connection error; it will retry automatically');
        };
    } catch (e) {
        console.log('SSE init failed, fallback to polling', e);
    }
}

// start SSE asap
try { startSSEEmailStatus(); } catch (e) {}
