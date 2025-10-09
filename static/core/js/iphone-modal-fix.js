/**
 * iPhone and iOS Safari Modal Fix
 * Addresses specific iPhone modal display issues including text cutoff and positioning
 */

(function() {
    'use strict';
    
    // Detect iPhone/iOS devices
    function isIOS() {
        return /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    }
    
    // Detect if device is iPhone specifically
    function isIPhone() {
        return /iPhone/.test(navigator.userAgent) && !window.MSStream;
    }
    
    // Store original scroll position
    let originalScrollPosition = 0;
    let originalBodyPosition = '';
    let originalBodyOverflow = '';
    
    // Fix modal positioning for iPhone
    function fixIPhoneModal() {
        if (!isIPhone()) return;
        
        // Store original values
        originalScrollPosition = window.pageYOffset || document.documentElement.scrollTop;
        originalBodyPosition = document.body.style.position;
        originalBodyOverflow = document.body.style.overflow;
        
        // Fix body positioning
        document.body.style.position = 'fixed';
        document.body.style.top = `-${originalScrollPosition}px`;
        document.body.style.width = '100%';
        document.body.style.overflow = 'hidden';
        
        // Fix modal positioning
        const modals = document.querySelectorAll('[id^="reminderModal"]');
        modals.forEach(function(modal) {
            const modalDialog = modal.querySelector('.modal-dialog');
            if (modalDialog) {
                // Ensure proper centering
                modalDialog.style.margin = '8px auto';
                modalDialog.style.maxWidth = 'calc(100vw - 16px)';
                modalDialog.style.width = 'calc(100vw - 16px)';
                
                // Fix content width
                const modalContent = modal.querySelector('.modal-content');
                if (modalContent) {
                    modalContent.style.width = '100%';
                    modalContent.style.maxWidth = '100%';
                }
            }
        });
    }
    
    // Restore original positioning
    function restoreIPhoneModal() {
        if (!isIPhone()) return;
        
        // Restore body styles
        document.body.style.position = originalBodyPosition;
        document.body.style.top = '';
        document.body.style.width = '';
        document.body.style.overflow = originalBodyOverflow;
        
        // Restore scroll position
        window.scrollTo(0, originalScrollPosition);
    }
    
    // Initialize when DOM is ready
    function init() {
        if (!isIOS()) return;
        
        // Fix modal events for reminder modals
        document.addEventListener('show.bs.modal', function(event) {
            const modal = event.target;
            if (modal && modal.id && modal.id.startsWith('reminderModal')) {
                fixIPhoneModal();
            }
        });
        
        document.addEventListener('hide.bs.modal', function(event) {
            const modal = event.target;
            if (modal && modal.id && modal.id.startsWith('reminderModal')) {
                restoreIPhoneModal();
            }
        });
        
        // Handle modal shown event for additional fixes
        document.addEventListener('shown.bs.modal', function(event) {
            const modal = event.target;
            if (modal && modal.id && modal.id.startsWith('reminderModal') && isIPhone()) {
                // Additional iPhone-specific fixes after modal is shown
                const modalDialog = modal.querySelector('.modal-dialog');
                if (modalDialog) {
                    // Force reflow to ensure proper positioning
                    modalDialog.offsetHeight;
                    
                    // Ensure modal is properly centered
                    modalDialog.style.transform = 'translate(0, 0)';
                }
            }
        });
        
        // Handle viewport changes (orientation change)
        window.addEventListener('orientationchange', function() {
            if (isIPhone()) {
                setTimeout(function() {
                    // Re-apply fixes after orientation change
                    const openModals = document.querySelectorAll('.modal.show');
                    if (openModals.length > 0) {
                        fixIPhoneModal();
                    }
                }, 100);
            }
        });
        
        // Handle window resize
        window.addEventListener('resize', function() {
            if (isIPhone()) {
                const openModals = document.querySelectorAll('.modal.show');
                if (openModals.length > 0) {
                    fixIPhoneModal();
                }
            }
        });
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
})();
