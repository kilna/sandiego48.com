document.addEventListener('DOMContentLoaded', function() {
  const filterButtons = document.querySelectorAll('.filter-btn');
  const personCards = document.querySelectorAll('.person-card');
  const countElement = document.getElementById('filter-count');

  function filterPeople(filterType) {
    let visibleCount = 0;
    
    personCards.forEach(card => {
      const roles = card.dataset.roles || '';
      
      if (filterType === 'all') {
        card.style.display = 'block';
        card.style.opacity = '1';
        card.style.transform = 'scale(1)';
        visibleCount++;
      } else {
        if (roles.includes(filterType)) {
          card.style.display = 'block';
          card.style.opacity = '1';
          card.style.transform = 'scale(1)';
          visibleCount++;
        } else {
          card.style.opacity = '0';
          card.style.transform = 'scale(0.8)';
          setTimeout(() => {
            if (card.style.opacity === '0') {
              card.style.display = 'none';
            }
          }, 300);
        }
      }
    });

    // Update count display
    if (countElement) {
      if (filterType === 'all') {
        countElement.textContent = `Showing all ${visibleCount} people`;
      } else {
        countElement.textContent = `Showing ${visibleCount} ${filterType.toLowerCase()}${visibleCount !== 1 ? 's' : ''}`;
      }
    }
  }

  // Add click handlers to filter buttons
  filterButtons.forEach(button => {
    button.addEventListener('click', function() {
      // Remove active class from all buttons
      filterButtons.forEach(btn => btn.classList.remove('active'));
      
      // Add active class to clicked button
      this.classList.add('active');
      
      // Filter people
      const filterType = this.dataset.filter;
      filterPeople(filterType);
    });
  });

  // Initialize with all people showing
  filterPeople('all');
}); 