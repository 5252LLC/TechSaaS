/**
 * TechSaaS.Tech - Interactive Website Script
 * Created: May 9, 2025
 */

document.addEventListener('DOMContentLoaded', function() {
    // Navigation scroll effect
    const nav = document.querySelector('nav');
    const menuToggle = document.querySelector('.menu-toggle');
    const navLinks = document.querySelector('.nav-links');
    
    // Mobile menu toggle
    menuToggle.addEventListener('click', function() {
        navLinks.classList.toggle('active');
    });
    
    // Close mobile menu when clicking a link
    document.querySelectorAll('.nav-links a').forEach(link => {
        link.addEventListener('click', function() {
            navLinks.classList.remove('active');
        });
    });
    
    // Add scrolled class to nav on scroll
    window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
            nav.classList.add('scrolled');
        } else {
            nav.classList.remove('scrolled');
        }
    });
    
    // Animate ecosystem graph
    animateEcosystemGraph();
    
    // Animate progress bars when they come into view
    animateOnScroll('.progress-bar', function(el) {
        // Get width from inline style
        const width = el.style.width;
        // First set width to 0
        el.style.width = '0';
        // Then animate to actual width
        setTimeout(() => {
            el.style.width = width;
        }, 100);
    });
    
    // Animate ecosystem metrics when they come into view
    animateOnScroll('.metric-value', function(el) {
        const value = el.textContent;
        el.textContent = '0';
        
        // Simple counter animation
        let current = 0;
        const target = parseInt(value);
        const duration = 2000; // 2 seconds
        const step = target / (duration / 16); // 60fps
        
        const counter = setInterval(() => {
            current += step;
            if (current >= target) {
                el.textContent = value; // Set to original value for correct formatting
                clearInterval(counter);
            } else {
                if (value.includes('%')) {
                    el.textContent = Math.floor(current) + '%';
                } else if (value.includes('+')) {
                    el.textContent = '+' + Math.floor(current) + '%';
                } else {
                    el.textContent = Math.floor(current);
                }
            }
        }, 16);
    });
});

/**
 * Animate elements when they come into view
 */
function animateOnScroll(selector, callback) {
    const elements = document.querySelectorAll(selector);
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                callback(entry.target);
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1
    });
    
    elements.forEach(el => {
        observer.observe(el);
    });
}

/**
 * Animate ecosystem graph nodes and connections
 */
function animateEcosystemGraph() {
    const nodes = document.querySelectorAll('.node');
    
    // Randomly move nodes slightly
    nodes.forEach(node => {
        setInterval(() => {
            const randomX = (Math.random() - 0.5) * 10;
            const randomY = (Math.random() - 0.5) * 10;
            
            node.style.transform = `translate(${randomX}px, ${randomY}px)`;
            
            setTimeout(() => {
                node.style.transform = 'translate(0, 0)';
            }, 500);
        }, 3000 + Math.random() * 2000);
    });
    
    // Line drawing animation for the timeline
    const timeline = document.querySelector('.timeline');
    if (!timeline) return;
    
    const timelineItems = document.querySelectorAll('.timeline-item');
    timelineItems.forEach((item, index) => {
        setTimeout(() => {
            item.style.opacity = '1';
            item.style.transform = 'translateX(0)';
        }, 300 * index);
    });
}

/**
 * Animate connections between ecosystem nodes
 */
function drawConnections() {
    const connectors = document.querySelectorAll('.connector');
    
    connectors.forEach((connector, index) => {
        setTimeout(() => {
            connector.style.width = '100%';
            connector.style.opacity = '0.5';
        }, 200 * index);
    });
}

// Draw connections on load (delayed for effect)
setTimeout(drawConnections, 1000);
