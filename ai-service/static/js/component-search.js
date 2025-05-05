/**
 * Component Showcase Search
 * Enables developers to quickly find UI components by name, category, or attributes
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
    const title = section.querySelector('.component-example-header').textContent;
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
  
  // Search function
  function performSearch() {
    const query = searchInput.value.toLowerCase().trim();
    let matchCount = 0;
    
    if (query === '') {
      // If search is empty, show all components
      componentData.forEach(component => {
        component.element.classList.remove('d-none');
        if (component.parentSection) {
          component.parentSection.classList.remove('d-none');
        }
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
    
    // Show matching components
    componentData.forEach(component => {
      if (
        component.title.toLowerCase().includes(query) || 
        component.category.toLowerCase().includes(query) ||
        component.content.includes(query)
      ) {
        component.element.classList.remove('d-none');
        if (component.parentSection) {
          component.parentSection.classList.remove('d-none');
        }
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
});
