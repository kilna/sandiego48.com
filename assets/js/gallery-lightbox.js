// Gallery Lightbox JavaScript
document.addEventListener('DOMContentLoaded', function() {
  // Initialize all galleries
  const galleries = document.querySelectorAll('.cdn-gallery');
  
  galleries.forEach(gallery => {
    const galleryType = gallery.dataset.type;
    const galleryLinks = gallery.querySelectorAll('.gallery-link');
    
    galleryLinks.forEach(link => {
      link.addEventListener('click', function(e) {
        e.preventDefault();
        const index = parseInt(this.dataset.index);
        const imageName = this.href.split('/').pop(); // Extract filename from URL
        openLightbox(galleryType + '-gallery', index, imageName);
      });
    });
  });
  
  // Initialize Load More buttons
  initializeLoadMoreButtons();
  
  // Handle URL hash on page load
  handleHashOnLoad();
  
  // Handle hash changes (back/forward buttons)
  window.addEventListener('hashchange', handleHashOnLoad);
  
  // Keyboard navigation
  document.addEventListener('keydown', function(e) {
    const activeLightbox = document.querySelector('.lightbox.active');
    if (!activeLightbox) return;
    
    const galleryId = activeLightbox.id;
    
    switch(e.key) {
      case 'Escape':
        closeLightbox(galleryId);
        break;
      case 'ArrowLeft':
        previousImage(galleryId);
        break;
      case 'ArrowRight':
        nextImage(galleryId);
        break;
    }
  });
});

function handleHashOnLoad() {
  const hash = window.location.hash.substring(1); // Remove the #
  if (!hash) return;
  
  // Find the gallery and image that matches the hash
  const galleries = document.querySelectorAll('.cdn-gallery');
  galleries.forEach(gallery => {
    const galleryType = gallery.dataset.type;
    const galleryLinks = gallery.querySelectorAll('.gallery-link');
    
    // First, try to find in existing loaded links
    let found = false;
    galleryLinks.forEach(link => {
      const imageName = link.href.split('/').pop();
      if (imageName === hash) {
        const index = parseInt(link.dataset.index);
        openLightbox(galleryType + '-gallery', index, imageName);
        found = true;
      }
    });
    
    // If not found in loaded links, try to extract index from hash and generate URL
    if (!found) {
      const match = hash.match(/^(.+?)(\d+)\.(.+)$/);
      if (match) {
        const prefix = match[1];
        const index = parseInt(match[2]);
        const extension = match[3];
        
        // Check if this matches our gallery pattern
        const loadMoreBtn = gallery.querySelector('.gallery-load-more-btn');
        if (loadMoreBtn) {
          const galleryPrefix = loadMoreBtn.dataset.prefix;
          const galleryExtension = loadMoreBtn.dataset.extension;
          
          if (prefix === galleryPrefix && extension === galleryExtension) {
            openLightbox(galleryType + '-gallery', index, hash);
          }
        }
      }
    }
  });
}

function openLightbox(galleryId, index, imageName) {
  const lightbox = document.getElementById('lightbox-' + galleryId);
  const gallery = document.querySelector(`[data-type="${galleryId.replace('-gallery', '')}"]`);
  
  if (!lightbox || !gallery) return;
  
  // Try to use existing link first, fall back to dynamic generation
  const links = gallery.querySelectorAll('.gallery-link');
  const totalImages = parseInt(gallery.dataset.totalImages);
  
  if (links.length > 0 && index <= links.length) {
    // Use existing link (for images that are already loaded)
    setLightboxImage(lightbox, links, index);
  } else {
    // Use dynamic generation for images beyond what's loaded
    const imageUrl = generateImageUrl(gallery, index);
    if (imageUrl) {
      setLightboxImageDynamic(lightbox, index, imageUrl, totalImages);
    } else {
      return; // Can't generate URL
    }
  }
  
  // Update URL hash
  if (imageName) {
    window.location.hash = imageName;
  }
  
  // Show lightbox
  lightbox.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeLightbox(galleryId) {
  const lightbox = document.getElementById('lightbox-' + galleryId);
  if (lightbox) {
    lightbox.classList.remove('active');
    document.body.style.overflow = '';
    
    // Clear URL hash
    if (window.location.hash) {
      window.history.replaceState(null, null, window.location.pathname);
    }
  }
}

function previousImage(galleryId) {
  const lightbox = document.getElementById('lightbox-' + galleryId);
  const gallery = document.querySelector(`[data-type="${galleryId.replace('-gallery', '')}"]`);
  const currentIndex = parseInt(lightbox.querySelector('.lightbox-current').textContent);
  const totalImages = parseInt(lightbox.querySelector('.lightbox-total').textContent);
  
  // Don't loop - stay at first image if already there
  if (currentIndex <= 1) return;
  
  const newIndex = currentIndex - 1;
  const imageUrl = generateImageUrl(gallery, newIndex);
  const imageName = imageUrl.split('/').pop();
  setLightboxImageDynamic(lightbox, newIndex, imageUrl, totalImages);
  
  // Update URL hash
  window.location.hash = imageName;
}

function nextImage(galleryId) {
  const lightbox = document.getElementById('lightbox-' + galleryId);
  const gallery = document.querySelector(`[data-type="${galleryId.replace('-gallery', '')}"]`);
  const currentIndex = parseInt(lightbox.querySelector('.lightbox-current').textContent);
  const totalImages = parseInt(lightbox.querySelector('.lightbox-total').textContent);
  
  // Don't loop - stay at last image if already there
  if (currentIndex >= totalImages) return;
  
  const newIndex = currentIndex + 1;
  const imageUrl = generateImageUrl(gallery, newIndex);
  const imageName = imageUrl.split('/').pop();
  setLightboxImageDynamic(lightbox, newIndex, imageUrl, totalImages);
  
  // Update URL hash
  window.location.hash = imageName;
}

function setLightboxImage(lightbox, links, index) {
  const link = links[index - 1]; // Convert to 0-based index
  const imageUrl = link.href;
  const imageAlt = link.dataset.title;
  
  const lightboxImage = lightbox.querySelector('.lightbox-image');
  const currentCounter = lightbox.querySelector('.lightbox-current');
  const totalCounter = lightbox.querySelector('.lightbox-total');
  const prevButton = lightbox.querySelector('.lightbox-prev');
  const nextButton = lightbox.querySelector('.lightbox-next');
  
  // Update image
  lightboxImage.src = imageUrl;
  lightboxImage.alt = imageAlt;
  
  // Update counter
  currentCounter.textContent = index;
  totalCounter.textContent = links.length;
  
  // Show/hide navigation arrows based on position
  if (prevButton) {
    prevButton.style.display = index > 1 ? 'block' : 'none';
  }
  if (nextButton) {
    nextButton.style.display = index < links.length ? 'block' : 'none';
  }
  
  // Preload adjacent images for smoother navigation (only if they exist)
  preloadAdjacentImages(links, index);
}

function preloadAdjacentImages(links, currentIndex) {
  const total = links.length;
  
  // Preload previous image (only if it exists)
  if (currentIndex > 1) {
    const prevIndex = currentIndex - 1;
    const prevImg = new Image();
    prevImg.src = links[prevIndex - 1].href;
  }
  
  // Preload next image (only if it exists)
  if (currentIndex < total) {
    const nextIndex = currentIndex + 1;
    const nextImg = new Image();
    nextImg.src = links[nextIndex - 1].href;
  }
}

// Generate image URL dynamically based on gallery configuration
function generateImageUrl(gallery, index) {
  const galleryData = gallery.dataset;
  const totalImages = parseInt(galleryData.totalImages);
  
  if (index < 1 || index > totalImages) {
    return '';
  }
  
  // Get gallery configuration from the first existing link (if any)
  const existingLinks = gallery.querySelectorAll('.gallery-link');
  if (existingLinks.length > 0) {
    // Use existing link pattern to determine URL structure
    const firstLink = existingLinks[0];
    const baseUrl = firstLink.href.replace(/\/[^/]+$/, ''); // Remove filename
    const filename = firstLink.href.split('/').pop();
    
    // Extract prefix and extension from filename
    const match = filename.match(/^(.+?)(\d+)\.(.+)$/);
    if (match) {
      const prefix = match[1];
      const extension = match[3];
      const padding = match[2].length; // Determine padding from existing filename
      const paddedIndex = index.toString().padStart(padding, '0');
      return `${baseUrl}/${prefix}${paddedIndex}.${extension}`;
    }
  }
  
  // Fallback: try to get configuration from load more button data attributes
  const loadMoreBtn = gallery.querySelector('.gallery-load-more-btn');
  if (loadMoreBtn) {
    const cdnUrl = loadMoreBtn.dataset.cdnUrl;
    const contentPath = loadMoreBtn.dataset.contentPath;
    const prefix = loadMoreBtn.dataset.prefix;
    const extension = loadMoreBtn.dataset.extension;
    const padding = parseInt(loadMoreBtn.dataset.padding);
    const paddedIndex = index.toString().padStart(padding, '0');
    const imageName = `${prefix}${paddedIndex}.${extension}`;
    return `${cdnUrl}/${contentPath}/${imageName}`;
  }
  
  return '';
}

// Set lightbox image dynamically (works with any image index, not just loaded ones)
function setLightboxImageDynamic(lightbox, index, imageUrl, totalImages) {
  const lightboxImage = lightbox.querySelector('.lightbox-image');
  const currentCounter = lightbox.querySelector('.lightbox-current');
  const totalCounter = lightbox.querySelector('.lightbox-total');
  const prevButton = lightbox.querySelector('.lightbox-prev');
  const nextButton = lightbox.querySelector('.lightbox-next');
  
  // Update image
  lightboxImage.src = imageUrl;
  lightboxImage.alt = `Gallery Image ${index}`;
  
  // Update counter
  currentCounter.textContent = index;
  totalCounter.textContent = totalImages;
  
  // Show/hide navigation arrows based on position
  if (prevButton) {
    prevButton.style.display = index > 1 ? 'block' : 'none';
  }
  if (nextButton) {
    nextButton.style.display = index < totalImages ? 'block' : 'none';
  }
  
  // Preload adjacent images for smoother navigation
  preloadAdjacentImagesDynamic(lightbox, index, totalImages);
}

// Preload adjacent images dynamically
function preloadAdjacentImagesDynamic(lightbox, currentIndex, totalImages) {
  const gallery = document.querySelector(`[data-type="${lightbox.id.replace('lightbox-', '').replace('-gallery', '')}"]`);
  
  // Preload previous image (only if it exists)
  if (currentIndex > 1) {
    const prevIndex = currentIndex - 1;
    const prevImageUrl = generateImageUrl(gallery, prevIndex);
    if (prevImageUrl) {
      const prevImg = new Image();
      prevImg.src = prevImageUrl;
    }
  }
  
  // Preload next image (only if it exists)
  if (currentIndex < totalImages) {
    const nextIndex = currentIndex + 1;
    const nextImageUrl = generateImageUrl(gallery, nextIndex);
    if (nextImageUrl) {
      const nextImg = new Image();
      nextImg.src = nextImageUrl;
    }
  }
}

// Close lightbox when clicking on background
document.addEventListener('click', function(e) {
  if (e.target.classList.contains('lightbox')) {
    const galleryId = e.target.id.replace('lightbox-', '');
    closeLightbox(galleryId);
  }
});

// Load More functionality
function initializeLoadMoreButtons() {
  const loadMoreButtons = document.querySelectorAll('.gallery-load-more-btn');
  
  loadMoreButtons.forEach(button => {
    button.addEventListener('click', function() {
      loadMoreImages(this);
    });
  });
}

function loadMoreImages(button) {
  const galleryId = button.dataset.gallery;
  const currentLoaded = parseInt(button.dataset.loaded);
  const totalImages = parseInt(button.dataset.total);
  const loadAmount = 24; // Load 24 more images at a time
  
  // Show loading state
  const loadMoreText = button.querySelector('.load-more-text');
  const loadMoreLoading = button.querySelector('.load-more-loading');
  
  loadMoreText.style.display = 'none';
  loadMoreLoading.style.display = 'flex';
  button.disabled = true;
  
  // Get gallery data
  const cdnUrl = button.dataset.cdnUrl;
  const contentPath = button.dataset.contentPath;
  const prefix = button.dataset.prefix;
  const extension = button.dataset.extension;
  const thumbSuffix = button.dataset.thumbSuffix;
  const thumbExt = button.dataset.thumbExt;
  const padding = parseInt(button.dataset.padding);
  const name = button.dataset.name;
  
  // Calculate how many images to load
  const nextBatch = Math.min(currentLoaded + loadAmount, totalImages);
  
  // Get the gallery grid
  const galleryGrid = document.getElementById(`gallery-grid-${galleryId}`);
  
  // Create new gallery items
  const fragment = document.createDocumentFragment();
  
  for (let i = currentLoaded + 1; i <= nextBatch; i++) {
    const paddedNum = i.toString().padStart(padding, '0');
    const imageName = `${prefix}${paddedNum}.${extension}`;
    const thumbName = `${prefix}${paddedNum}${thumbSuffix}.${thumbExt}`;
    const imageURL = `${cdnUrl}/${contentPath}/${imageName}`;
    const thumbURL = `${cdnUrl}/${contentPath}/thumbs/${thumbName}`;
    
    const galleryItem = document.createElement('div');
    galleryItem.className = 'gallery-item';
    
    const link = document.createElement('a');
    link.href = imageURL;
    link.className = 'gallery-link';
    link.dataset.gallery = `${galleryId}-gallery`;
    link.dataset.index = i;
    link.dataset.title = `${name} ${i}`;
    
    const img = document.createElement('img');
    img.src = thumbURL;
    img.alt = `${name} ${i}`;
    img.loading = 'lazy';
    
    link.appendChild(img);
    galleryItem.appendChild(link);
    fragment.appendChild(galleryItem);
    
    // Add click event listener for lightbox
    link.addEventListener('click', function(e) {
      e.preventDefault();
      const index = parseInt(this.dataset.index);
      const imageName = this.href.split('/').pop();
      openLightbox(galleryId + '-gallery', index, imageName);
    });
  }
  
  // Add new items to gallery
  galleryGrid.appendChild(fragment);
  
  // Update button state
  button.dataset.loaded = nextBatch;
  
  // Update remaining count
  const remainingCount = totalImages - nextBatch;
  const countSpan = button.querySelector('.load-more-count');
  
  if (remainingCount > 0) {
    countSpan.textContent = `(${remainingCount} more)`;
    // Reset button state
    loadMoreText.style.display = 'flex';
    loadMoreLoading.style.display = 'none';
    button.disabled = false;
  } else {
    // Hide button when all images are loaded
    button.parentElement.style.display = 'none';
  }
  
  // Update lightbox total count for this gallery
  const lightbox = document.getElementById(`lightbox-${galleryId}-gallery`);
  if (lightbox) {
    const totalCounter = lightbox.querySelector('.lightbox-total');
    if (totalCounter) {
      totalCounter.textContent = nextBatch;
    }
  }
}
