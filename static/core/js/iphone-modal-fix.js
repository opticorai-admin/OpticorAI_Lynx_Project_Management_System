/**
 * iPhone and iOS Safari Modal Fix - Anti-Freeze Version
 * Addresses iPhone modal display issues without causing screen freezing
 */

(function() {
    'use strict';
    
    // Detect iPhone specifically
    function isIPhone() {
        return /iPhone/.test(navigator.userAgent) && !window.MSStream;
    }
    
    // Store original values
    let originalBodyOverflow = '';
    let originalBodyPaddingRight = '';
    
    // Safe modal fix for iPhone (prevents freezing)
    function fixIPhoneModal() {
        if (!isIPhone()) return;
        
        // Store original values
        originalBodyOverflow = document.body.style.overflow;
        originalBodyPaddingRight = document.body.style.paddingRight;
        
        // Prevent background scroll without freezing
        document.body.style.overflow = 'hidden';
        document.documentElement.style.overflow = 'hidden';
        
        // Fix modal positioning without touching body position
        const modals = document.querySelectorAll('[id^="reminderModal"]');
        modals.forEach(function(modal) {
            const modalDialog = modal.querySelector('.modal-dialog');
            if (modalDialog) {
                // Ensure proper centering and width
                modalDialog.style.margin = '10px auto';
                modalDialog.style.maxWidth = 'calc(100vw - 20px)';
                modalDialog.style.width = 'calc(100vw - 20px)';
                modalDialog.style.position = 'relative';
                modalDialog.style.left = 'auto';
                modalDialog.style.right = 'auto';
                modalDialog.style.transform = 'none';
                
                // Fix content width
                const modalContent = modal.querySelector('.modal-content');
                if (modalContent) {
                    modalContent.style.width = '100%';
                    modalContent.style.maxWidth = '100%';
                    modalContent.style.margin = '0';
                    modalContent.style.borderRadius = '8px';
                }
                
                // Fix header text cutoff
                const modalHeader = modal.querySelector('.modal-header');
                if (modalHeader) {
                    modalHeader.style.padding = '15px 20px';
                    modalHeader.style.position = 'relative';
                }
                
                // Fix title text cutoff
                const modalTitle = modal.querySelector('.modal-title');
                if (modalTitle) {
                    modalTitle.style.paddingRight = '50px';
                    modalTitle.style.wordWrap = 'break-word';
                    modalTitle.style.overflowWrap = 'break-word';
                    modalTitle.style.hyphens = 'auto';
                }
                
                // Fix body content
                const modalBody = modal.querySelector('.modal-body');
                if (modalBody) {
                    modalBody.style.padding = '20px';
                    modalBody.style.wordWrap = 'break-word';
                    modalBody.style.overflowWrap = 'break-word';
                }
                
                // Fix form elements
                const formControls = modal.querySelectorAll('.form-control');
                formControls.forEach(function(control) {
                    control.style.width = '100%';
                    control.style.boxSizing = 'border-box';
                    control.style.fontSize = '16px'; // Prevent zoom
                });
                
                // Fix footer
                const modalFooter = modal.querySelector('.modal-footer');
                if (modalFooter) {
                    modalFooter.style.padding = '15px 20px';
                    modalFooter.style.display = 'flex';
                    modalFooter.style.gap = '10px';
                }
                
                // Fix close button positioning
                const closeBtn = modal.querySelector('.close');
                if (closeBtn) {
                    closeBtn.style.position = 'absolute';
                    closeBtn.style.top = '15px';
                    closeBtn.style.right = '20px';
                    closeBtn.style.padding = '8px';
                    closeBtn.style.zIndex = '1051';
                }
            }
        });
    }
    
    // Safe restore function
    function restoreIPhoneModal() {
        if (!isIPhone()) return;
        
        // Restore body styles safely
        document.body.style.overflow = originalBodyOverflow;
        document.body.style.paddingRight = originalBodyPaddingRight;
        document.documentElement.style.overflow = '';
    }
    
    // Initialize when DOM is ready
    function init() {
        if (!isIPhone()) return;
        
        // Fix modal events for reminder modals
        document.addEventListener('show.bs.modal', function(event) {
            const modal = event.target;
            if (modal && modal.id && modal.id.startsWith('reminderModal')) {
                // Delay fix to ensure modal is ready
                setTimeout(fixIPhoneModal, 50);
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
            if (modal && modal.id && modal.id.startsWith('reminderModal')) {
                // Re-apply fixes after modal is fully shown
                setTimeout(fixIPhoneModal, 100);
            }
        });
        
        // Handle viewport changes (orientation change) - prevent freezing
        window.addEventListener('orientationchange', function() {
            setTimeout(function() {
                const openModals = document.querySelectorAll('.modal.show [id^="reminderModal"]');
                if (openModals.length > 0) {
                    fixIPhoneModal();
                }
            }, 200);
        });
        
        // Handle window resize - prevent excessive calls
        let resizeTimeout;
        window.addEventListener('resize', function() {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(function() {
                const openModals = document.querySelectorAll('.modal.show [id^="reminderModal"]');
                if (openModals.length > 0) {
                    fixIPhoneModal();
                }
            }, 100);
        });
        
        // Add CSS class for iPhone-specific styling
        document.documentElement.classList.add('iphone-device');
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
})();
