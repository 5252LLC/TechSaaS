/**
 * TechSaaS - Main JavaScript
 * 
 * This file contains core JavaScript functionality for the TechSaaS application.
 */

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Handle card hover effects
    const cards = document.querySelectorAll('.card-hover');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.classList.add('shadow-lg');
        });
        
        card.addEventListener('mouseleave', function() {
            this.classList.remove('shadow-lg');
        });
    });
    
    // Initialize copy URL buttons with simple implementation
    initializeCopyButtons();
});

// Function to initialize all copy buttons on the page
function initializeCopyButtons() {
    document.querySelectorAll('.copy-url-btn').forEach(button => {
        button.addEventListener('click', function() {
            const url = this.getAttribute('data-url');
            if (!url || url === '') {
                console.error('No URL to copy');
                showCopyResult(this, false);
                return;
            }
            
            try {
                copyTextToClipboard(url, this);
            } catch (err) {
                console.error('Error copying text: ', err);
                showCopyResult(this, false);
            }
        });
    });
}

// Function to copy text to clipboard
function copyTextToClipboard(text, buttonElement) {
    // Create temporary element
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    textarea.style.top = '0';
    document.body.appendChild(textarea);
    
    try {
        // Select and copy
        textarea.focus();
        textarea.select();
        const successful = document.execCommand('copy');
        
        if (successful) {
            showCopyResult(buttonElement, true);
        } else {
            showCopyResult(buttonElement, false);
        }
    } catch (err) {
        console.error('Error during copy operation', err);
        showCopyResult(buttonElement, false);
    } finally {
        // Clean up
        document.body.removeChild(textarea);
    }
}

// Function to show copy result feedback
function showCopyResult(buttonElement, success) {
    const originalHTML = buttonElement.innerHTML;
    const originalClasses = [...buttonElement.classList];
    
    if (success) {
        buttonElement.innerHTML = '<i class="fas fa-check me-1"></i> Copied!';
        buttonElement.classList.remove('btn-outline-info', 'btn-danger');
        buttonElement.classList.add('btn-success');
    } else {
        buttonElement.innerHTML = '<i class="fas fa-times me-1"></i> Failed!';
        buttonElement.classList.remove('btn-outline-info', 'btn-success');
        buttonElement.classList.add('btn-danger');
    }
    
    // Reset button after 2 seconds
    setTimeout(() => {
        buttonElement.innerHTML = originalHTML;
        
        // Reset classes
        buttonElement.className = '';
        originalClasses.forEach(cls => {
            if (!['btn-success', 'btn-danger'].includes(cls)) {
                buttonElement.classList.add(cls);
            }
        });
        if (!buttonElement.classList.contains('btn-danger')) {
            buttonElement.classList.add('btn-outline-info');
        }
    }, 2000);
}

// Modern clipboard API
function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
        // Modern browsers with secure context
        return navigator.clipboard.writeText(text);
    } else {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.left = '0';
        textarea.style.top = '0';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        
        try {
            // Execute the copy command
            const successful = document.execCommand('copy');
            if (!successful) {
                console.error('Failed to copy text');
            }
        } catch (err) {
            console.error('Error during copy operation', err);
        }
        
        document.body.removeChild(textarea);
    }
}
