/**
 * Smooth Transitions for Role Switching
 */
class SmoothTransitions {
    constructor() {
        this.transitionDuration = 200;
        this.fadeInDuration = 300;
    }

    /**
     * Smooth fade out and fade in for section changes
     */
    async fadeOutIn(element, newContent, callback) {
        if (!element) return;

        // Fade out
        element.style.transition = `opacity ${this.transitionDuration}ms ease-out`;
        element.style.opacity = '0';

        // Wait for fade out
        await new Promise(resolve => setTimeout(resolve, this.transitionDuration));

        // Update content
        if (callback) callback();

        // Fade in
        element.style.opacity = '1';
        element.style.transition = `opacity ${this.fadeInDuration}ms ease-in`;

        // Wait for fade in
        await new Promise(resolve => setTimeout(resolve, this.fadeInDuration));
    }

    /**
     * Smooth loading state for tables
     */
    showTableLoading(tableBody) {
        if (!tableBody) return;

        tableBody.style.transition = 'opacity 0.2s ease';
        tableBody.style.opacity = '0.5';
        
        // Add loading class
        tableBody.classList.add('loading');
    }

    hideTableLoading(tableBody) {
        if (!tableBody) return;

        tableBody.style.opacity = '1';
        tableBody.classList.remove('loading');
    }

    /**
     * Smooth button state transitions
     */
    animateButtonState(button, state) {
        if (!button) return;

        button.style.transition = 'all 0.2s ease';
        
        switch(state) {
            case 'loading':
                button.disabled = true;
                button.style.opacity = '0.7';
                button.style.transform = 'scale(0.95)';
                break;
            case 'success':
                button.style.backgroundColor = '#28a745';
                button.style.color = 'white';
                setTimeout(() => {
                    button.style.backgroundColor = '';
                    button.style.color = '';
                    button.disabled = false;
                    button.style.opacity = '1';
                    button.style.transform = 'scale(1)';
                }, 1000);
                break;
            case 'error':
                button.style.backgroundColor = '#dc3545';
                button.style.color = 'white';
                setTimeout(() => {
                    button.style.backgroundColor = '';
                    button.style.color = '';
                    button.disabled = false;
                    button.style.opacity = '1';
                    button.style.transform = 'scale(1)';
                }, 1000);
                break;
            default:
                button.disabled = false;
                button.style.opacity = '1';
                button.style.transform = 'scale(1)';
        }
    }

    /**
     * Smooth progress indicator
     */
    showProgress(container, duration = 1000) {
        if (!container) return;

        const progress = document.createElement('div');
        progress.className = 'smooth-progress';
        progress.innerHTML = `
            <div class="progress-bar" style="width: 0%; transition: width ${duration}ms ease;"></div>
        `;

        container.appendChild(progress);

        // Animate progress
        setTimeout(() => {
            const progressBar = progress.querySelector('.progress-bar');
            if (progressBar) {
                progressBar.style.width = '100%';
            }
        }, 50);

        // Remove progress after completion
        setTimeout(() => {
            progress.remove();
        }, duration + 100);
    }
}

// Initialize global instance
window.smoothTransitions = new SmoothTransitions();

// Add CSS for smooth transitions
const style = document.createElement('style');
style.textContent = `
    .smooth-progress {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background-color: #e9ecef;
        overflow: hidden;
        z-index: 1000;
    }
    
    .smooth-progress .progress-bar {
        height: 100%;
        background: linear-gradient(90deg, #007bff, #28a745);
        border-radius: 2px;
    }
    
    .loading {
        position: relative;
    }
    
    .loading::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
        animation: shimmer 1.5s infinite;
        pointer-events: none;
    }
    
    @keyframes shimmer {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }
`;
document.head.appendChild(style);
