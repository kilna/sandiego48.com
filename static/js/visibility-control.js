document.addEventListener('DOMContentLoaded', function() {
  // Find all elements with visibility time classes
  const elements = document.querySelectorAll('[class*="visible-after-"], [class*="visible-before-"]');
  
  elements.forEach(element => {
    const classes = element.className.split(' ');
    let visibleAfter = null;
    let visibleBefore = null;
    
    // Extract time classes
    classes.forEach(className => {
      if (className.startsWith('visible-after-')) {
        // Convert from URL-safe format back to ISO format
        const timeStr = className.replace('visible-after-', '').replace(/-/g, ':').replace('T', 'T');
        visibleAfter = new Date(timeStr);
      } else if (className.startsWith('visible-before-')) {
        const timeStr = className.replace('visible-before-', '').replace(/-/g, ':').replace('T', 'T');
        visibleBefore = new Date(timeStr);
      }
    });
    
    const now = new Date();
    
    // Check if element should be visible initially
    const shouldBeVisible = (!visibleAfter || now >= visibleAfter) && (!visibleBefore || now < visibleBefore);
    
    if (!shouldBeVisible) {
      element.style.display = 'none';
      
      // Set up an interval to check every minute
      const checkInterval = setInterval(() => {
        const currentTime = new Date();
        const shouldShow = (!visibleAfter || currentTime >= visibleAfter) && (!visibleBefore || currentTime < visibleBefore);
        
        if (shouldShow) {
          element.style.display = '';  // Show element by removing inline style
          clearInterval(checkInterval);  // Stop checking once visible
        } else if (visibleBefore && currentTime >= visibleBefore) {
          // If we've passed the visible-before time, we can stop checking
          clearInterval(checkInterval);
        }
      }, 60000);  // Check every minute
    }
  });
}); 