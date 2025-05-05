/**
 * Component Showcase Search
 * Enables developers to quickly find UI components by name, category, or attributes
 * Enhanced with animations and accessibility features
 */
document.addEventListener('DOMContentLoaded', function() {
  // Select the search input and component containers
  const searchInput = document.getElementById('component-search');
  const componentSections = document.querySelectorAll('.component-example');
  const componentContainers = document.querySelectorAll('.component-section');
  const noResultsMessage = document.getElementById('no-results-message');
  
  // Initialize component data for search
  const componentData = [];
  
  // Set up component data for search
  componentSections.forEach(section => {
    const id = section.id;
    const title = section.querySelector('.component-example-header') ? 
      section.querySelector('.component-example-header').textContent : '';
    const parentSection = section.closest('.component-section');
    const category = parentSection ? parentSection.querySelector('.section-title').textContent : '';
    const content = section.textContent.toLowerCase();
    
    // Store all component data for searching
    componentData.push({
      id: id,
      title: title,
      category: category,
      element: section,
      parentSection: parentSection,
      content: content
    });
  });
  
  // Search function with enhanced animation
  function performSearch() {
    const query = searchInput.value.toLowerCase().trim();
    let matchCount = 0;
    
    if (query === '') {
      // If search is empty, show all components with staggered animation
      componentData.forEach((component, index) => {
        setTimeout(() => {
          component.element.classList.remove('d-none');
          component.element.style.opacity = '0';
          component.element.style.transform = 'translateY(20px)';
          
          // Trigger reflow
          component.element.offsetHeight;
          
          // Apply transition
          component.element.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
          component.element.style.opacity = '1';
          component.element.style.transform = 'translateY(0)';
          
          if (component.parentSection) {
            component.parentSection.classList.remove('d-none');
          }
        }, index * 50); // Stagger the animations
      });
      
      if (noResultsMessage) {
        noResultsMessage.classList.add('d-none');
      }
      
      return;
    }
    
    // Hide all components first
    componentData.forEach(component => {
      component.element.classList.add('d-none');
    });
    
    // Show matching components with animation
    componentData.forEach((component, index) => {
      if (
        component.title.toLowerCase().includes(query) || 
        component.category.toLowerCase().includes(query) ||
        component.content.includes(query)
      ) {
        setTimeout(() => {
          component.element.classList.remove('d-none');
          component.element.style.opacity = '0';
          component.element.style.transform = 'translateY(20px)';
          
          // Trigger reflow
          component.element.offsetHeight;
          
          // Apply transition
          component.element.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
          component.element.style.opacity = '1';
          component.element.style.transform = 'translateY(0)';
          
          if (component.parentSection) {
            component.parentSection.classList.remove('d-none');
          }
        }, index * 50); // Stagger the animations
        
        matchCount++;
      }
    });
    
    // Show/hide no results message
    if (noResultsMessage) {
      if (matchCount === 0) {
        noResultsMessage.classList.remove('d-none');
        noResultsMessage.textContent = `No components found matching "${query}"`;
      } else {
        noResultsMessage.classList.add('d-none');
      }
    }
    
    // Update search count
    const searchCount = document.getElementById('search-count');
    if (searchCount) {
      if (matchCount > 0) {
        searchCount.textContent = `Found ${matchCount} component${matchCount !== 1 ? 's' : ''}`;
        searchCount.classList.remove('d-none');
      } else {
        searchCount.classList.add('d-none');
      }
    }
    
    // Announce results to screen readers
    announceToScreenReader(`${matchCount} components found for search term ${query}`);
  }
  
  // Accessibility feature: Announce search results to screen readers
  function announceToScreenReader(message) {
    let ariaLive = document.getElementById('search-results-live');
    
    if (!ariaLive) {
      ariaLive = document.createElement('div');
      ariaLive.id = 'search-results-live';
      ariaLive.className = 'sr-only';
      ariaLive.setAttribute('aria-live', 'polite');
      ariaLive.setAttribute('aria-atomic', 'true');
      document.body.appendChild(ariaLive);
    }
    
    ariaLive.textContent = message;
  }
  
  // Add event listeners
  if (searchInput) {
    searchInput.addEventListener('input', performSearch);
    searchInput.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        searchInput.value = '';
        performSearch();
      }
    });
    
    // Clear search button
    const clearButton = document.getElementById('clear-search');
    if (clearButton) {
      clearButton.addEventListener('click', function() {
        searchInput.value = '';
        performSearch();
        searchInput.focus();
      });
    }
    
    // Add keyboard shortcut for search focus (Press '/' to focus search)
    document.addEventListener('keydown', function(e) {
      if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
        e.preventDefault();
        searchInput.focus();
      }
    });
  }
  
  // Initial focus on search if URL has search param
  if (window.location.search.includes('search=')) {
    const urlParams = new URLSearchParams(window.location.search);
    const searchParam = urlParams.get('search');
    if (searchParam && searchInput) {
      searchInput.value = searchParam;
      performSearch();
      searchInput.focus();
    }
  }
  
  // Add keyboard focus visual cue
  componentSections.forEach(section => {
    section.addEventListener('focusin', function() {
      this.classList.add('component-focus');
    });
    
    section.addEventListener('focusout', function() {
      this.classList.remove('component-focus');
    });
  });
  
  // Add tooltip explaining the keyboard shortcut
  if (searchInput) {
    const searchWrapper = searchInput.closest('.component-search-wrapper');
    if (searchWrapper) {
      const shortcutTip = document.createElement('small');
      shortcutTip.className = 'text-muted d-block text-end mt-1';
      shortcutTip.innerHTML = 'Press <kbd>/</kbd> to search';
      searchWrapper.appendChild(shortcutTip);
    }
  }
});
