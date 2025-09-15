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
    
    galleryLinks.forEach(link => {
      const imageName = link.href.split('/').pop();
      if (imageName === hash) {
        const index = parseInt(link.dataset.index);
        openLightbox(galleryType + '-gallery', index, imageName);
      }
    });
  });
}

function openLightbox(galleryId, index, imageName) {
  const lightbox = document.getElementById('lightbox-' + galleryId);
  const gallery = document.querySelector(`[data-type="${galleryId.replace('-gallery', '')}"]`);
  const links = gallery.querySelectorAll('.gallery-link');
  
  if (!lightbox || !links.length) return;
  
  // Set current image
  setLightboxImage(lightbox, links, index);
  
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
  const links = gallery.querySelectorAll('.gallery-link');
  const currentIndex = parseInt(lightbox.querySelector('.lightbox-current').textContent);
  
  // Don't loop - stay at first image if already there
  if (currentIndex <= 1) return;
  
  const newIndex = currentIndex - 1;
  const newImageName = links[newIndex - 1].href.split('/').pop();
  setLightboxImage(lightbox, links, newIndex);
  
  // Update URL hash
  window.location.hash = newImageName;
}

function nextImage(galleryId) {
  const lightbox = document.getElementById('lightbox-' + galleryId);
  const gallery = document.querySelector(`[data-type="${galleryId.replace('-gallery', '')}"]`);
  const links = gallery.querySelectorAll('.gallery-link');
  const currentIndex = parseInt(lightbox.querySelector('.lightbox-current').textContent);
  
  // Don't loop - stay at last image if already there
  if (currentIndex >= links.length) return;
  
  const newIndex = currentIndex + 1;
  const newImageName = links[newIndex - 1].href.split('/').pop();
  setLightboxImage(lightbox, links, newIndex);
  
  // Update URL hash
  window.location.hash = newImageName;
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

// Close lightbox when clicking on background
document.addEventListener('click', function(e) {
  if (e.target.classList.contains('lightbox')) {
    const galleryId = e.target.id.replace('lightbox-', '');
    closeLightbox(galleryId);
  }
});
