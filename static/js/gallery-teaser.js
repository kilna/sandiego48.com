// Gallery teaser with rotating random photos
document.addEventListener('DOMContentLoaded', function() {
  const teasers = document.querySelectorAll('.cdn-gallery-teaser');
  
  teasers.forEach(teaser => {
    const previewCount = parseInt(teaser.dataset.previewCount) || 6;
    const totalImages = parseInt(teaser.dataset.totalImages);
    const cdnUrl = teaser.dataset.cdnUrl;
    const contentPath = teaser.dataset.contentPath;
    const prefix = teaser.dataset.prefix;
    const thumbSuffix = teaser.dataset.thumbSuffix;
    const thumbExt = teaser.dataset.thumbExt;
    const padding = parseInt(teaser.dataset.padding);
    const galleryName = teaser.dataset.galleryName;
    const eventUrl = teaser.dataset.eventUrl;
    const grid = teaser.querySelector('.gallery-grid-teaser');
    
    // Create initial empty slots
    const slots = [];
    for (let i = 0; i < previewCount; i++) {
      const item = document.createElement('div');
      item.className = 'gallery-item';
      item.innerHTML = `
        <a href="${eventUrl}#gallery-photo" class="gallery-teaser-link">
          <img src="" alt="${galleryName}" loading="eager">
        </a>
      `;
      grid.appendChild(item);
      slots.push(item.querySelector('img'));
    }
    
    // Keep track of used images
    let usedImages = new Set();
    
    // Function to get random image number not currently shown
    function getRandomImageNum() {
      if (usedImages.size >= totalImages) {
        usedImages.clear(); // Reset if we've used all images
      }
      
      let num;
      do {
        num = Math.floor(Math.random() * totalImages) + 1;
      } while (usedImages.has(num));
      
      usedImages.add(num);
      return num;
    }
    
    // Function to update a single slot with new image
    function updateSlot(slot) {
      const num = getRandomImageNum();
      const paddedNum = String(num).padStart(padding, '0');
      const thumbUrl = `${cdnUrl}/${contentPath}/thumbs/${prefix}${paddedNum}${thumbSuffix}.${thumbExt}`;
      
      // Fade out
      slot.style.opacity = '0';
      
      // Update image after fade
      setTimeout(() => {
        slot.src = thumbUrl;
        slot.alt = `${galleryName} ${num}`;
        slot.style.opacity = '1';
      }, 250);
    }
    
    // Initialize all slots with random images
    slots.forEach(slot => updateSlot(slot));
    
    // Rotate images every 2 seconds
    setInterval(() => {
      // Pick a random slot to update
      const randomSlot = slots[Math.floor(Math.random() * slots.length)];
      updateSlot(randomSlot);
    }, 2000);
  });
});

