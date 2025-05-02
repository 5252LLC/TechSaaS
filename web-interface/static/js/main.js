/**
 * TechSaaS Platform - Main JavaScript
 * Provides interactive functionality and animation effects
 * for the TechSaaS web interface
 */

document.addEventListener('DOMContentLoaded', function() {
    // Theme toggle functionality
    initThemeToggle();
    
    // Add animation effects to feature cards on homepage
    animateFeatureCards();
    
    // Add hover effects for interactive elements
    addHoverEffects();
    
    // Initialize tab functionality
    initTabSwitching();
    
    // Add particle background effect if container exists
    initParticleBackground();
});

/**
 * Initialize theme toggle functionality with local storage persistence
 */
function initThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    
    if (!themeToggle) return;
    
    // Check if user has a saved preference
    const darkMode = localStorage.getItem('darkMode');
    
    // Set initial state based on saved preference
    if (darkMode === 'enabled') {
        themeToggle.checked = true;
        document.body.classList.add('light-mode');
    }
    
    // Toggle theme on change
    themeToggle.addEventListener('change', function() {
        if (this.checked) {
            document.body.classList.add('light-mode');
            localStorage.setItem('darkMode', 'enabled');
        } else {
            document.body.classList.remove('light-mode');
            localStorage.setItem('darkMode', 'disabled');
        }
    });
}

/**
 * Add staggered fade-in animation to feature cards
 */
function animateFeatureCards() {
    const cards = document.querySelectorAll('.feature-card');
    
    if (cards.length === 0) return;
    
    cards.forEach((card, index) => {
        setTimeout(() => {
            card.classList.add('fade-in');
        }, 100 * index);
    });
}

/**
 * Add hover effects to interactive elements
 */
function addHoverEffects() {
    // Add subtle scale effect to buttons
    const buttons = document.querySelectorAll('.btn:not(.btn-primary)');
    
    buttons.forEach(button => {
        button.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.05)';
        });
        
        button.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });
    
    // Add glow effect to cards on hover
    const cards = document.querySelectorAll('.feature-card, .result-item');
    
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.boxShadow = '0 8px 32px rgba(74, 108, 247, 0.15)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.3)';
        });
    });
}

/**
 * Initialize tab switching functionality
 */
function initTabSwitching() {
    // Process tab container if it exists
    const tabContainer = document.querySelector('.tab-container');
    
    if (tabContainer) {
        const tabs = tabContainer.querySelectorAll('.tab');
        
        tabs.forEach(tab => {
            tab.addEventListener('click', function() {
                // Get the active tab content ID from the tab ID
                const contentId = this.id.replace('-tab', '-content');
                
                // Remove active class from all tabs and contents
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                
                // Add active class to clicked tab and corresponding content
                this.classList.add('active');
                document.getElementById(contentId).classList.add('active');
            });
        });
        
        // Expose showTab function globally
        window.showTab = function(tabId) {
            document.getElementById(tabId).click();
        };
    }
}

/**
 * Initialize particle background effect for empty state
 */
function initParticleBackground() {
    const particlesContainer = document.querySelector('.particles');
    
    if (!particlesContainer) return;
    
    // Create particles with random positions and animations
    for (let i = 0; i < 50; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        
        // Random positioning
        particle.style.left = `${Math.random() * 100}%`;
        particle.style.top = `${Math.random() * 100}%`;
        
        // Random size
        const size = 2 + Math.random() * 4;
        particle.style.width = `${size}px`;
        particle.style.height = `${size}px`;
        
        // Random animation delay and duration
        particle.style.animationDelay = `${Math.random() * 5}s`;
        particle.style.animationDuration = `${5 + Math.random() * 10}s`;
        
        particlesContainer.appendChild(particle);
    }
}

/**
 * Shows a notification toast message
 * @param {string} message - The message to display
 * @param {string} type - The type of notification (success, error, warning)
 * @param {number} duration - Duration in milliseconds
 */
function showNotification(message, type = 'success', duration = 3000) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Add to document
    document.body.appendChild(notification);
    
    // Show with animation
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // Remove after duration
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, duration);
}

// Make utility functions globally available
window.showNotification = showNotification;
