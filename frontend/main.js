// Canvas and Context Setup
const canvas = document.getElementById("scroll-canvas");
const context = canvas.getContext("2d");

const frameCount = 265;
// Helper function to resolve frame paths
const currentFrame = index => (
  `./ezgif-8afa6143e4a4a9a1-jpg/ezgif-frame-${index.toString().padStart(3, '0')}.jpg`
);

// Preloader Progress Elements
const preloader = document.getElementById("preloader");
const progressBar = document.getElementById("progress-bar");
const progressPercentage = document.getElementById("progress-percentage");
const statusMsg = document.getElementById("status-msg");

// Animated Content Elements
const heroSection = document.getElementById("hero-section");
const scrollIndicator = document.getElementById("scroll-indicator");

// Array to store preloaded image objects
const images = [];
let loadedCount = 0;

// Dynamic status messages to display during loading phase
const statusPhrases = [
  "Initializing AI assets...",
  "Preloading canvas frames...",
  "Calibrating interactive triggers...",
  "Rendering digital workspace graphics...",
  "Ready to explore..."
];

// Preload all frames sequentially
function preloadImages() {
  return new Promise((resolve) => {
    for (let i = 1; i <= frameCount; i++) {
      const img = new Image();
      img.src = currentFrame(i);
      img.onload = () => {
        loadedCount++;
        const percent = Math.floor((loadedCount / frameCount) * 100);
        
        // Update loader progress UI
        progressBar.style.width = `${percent}%`;
        progressPercentage.textContent = `${percent}%`;
        
        const phraseIdx = Math.min(
          statusPhrases.length - 1,
          Math.floor((loadedCount / frameCount) * statusPhrases.length)
        );
        statusMsg.textContent = statusPhrases[phraseIdx];

        if (loadedCount === frameCount) {
          // Delay fading out the preloader to feel smooth
          setTimeout(() => {
            preloader.classList.add("fade-out");
            resolve();
          }, 500);
        }
      };
      
      img.onerror = () => {
        loadedCount++;
        console.warn(`Frame failed to load: ${img.src}`);
        if (loadedCount === frameCount) {
          preloader.classList.add("fade-out");
          resolve();
        }
      };
      images.push(img);
    }
  });
}

// Responsive canvas image rendering
function renderImage(img) {
  if (!img) return;

  const canvasWidth = window.innerWidth;
  const canvasHeight = window.innerHeight;

  // Use device pixel ratio for crisp rendering on Retina / High-DPI screens
  const dpr = window.devicePixelRatio || 1;
  canvas.width = canvasWidth * dpr;
  canvas.height = canvasHeight * dpr;
  
  // Scale the context to draw in virtual pixels
  context.scale(dpr, dpr);

  const imgWidth = img.naturalWidth || img.width;
  const imgHeight = img.naturalHeight || img.height;

  const imgRatio = imgWidth / imgHeight;
  const canvasRatio = canvasWidth / canvasHeight;

  let drawWidth, drawHeight, drawX, drawY;

  // Calculate coordinates to cover viewport (similar to CSS background-size: cover)
  if (imgRatio > canvasRatio) {
    drawHeight = canvasHeight;
    drawWidth = canvasHeight * imgRatio;
    drawX = (canvasWidth - drawWidth) / 2;
    drawY = 0;
  } else {
    drawWidth = canvasWidth;
    drawHeight = canvasWidth / imgRatio;
    drawX = 0;
    drawY = (canvasHeight - drawHeight) / 2;
  }

  context.clearRect(0, 0, canvasWidth, canvasHeight);
  context.drawImage(img, drawX, drawY, drawWidth, drawHeight);
}

// Scroll mapping & smooth interpolation (lerp)
let targetScrollProgress = 0;
let currentScrollProgress = 0;
const ease = 0.08; // Butter-smooth scroll animation easing factor
let lastRenderedFrame = -1;

function updateScrollProgress() {
  const scrollTop = window.scrollY;
  // Map progress (0.0 to 1.0) specifically over 300vh (3 * window.innerHeight)
  const animScrollHeight = window.innerHeight * 3;
  targetScrollProgress = Math.min(1, Math.max(0, scrollTop / animScrollHeight));
}

// Handles browser resize
function handleResize() {
  const frameIndex = Math.min(
    frameCount - 1,
    Math.max(0, Math.floor(currentScrollProgress * (frameCount - 1)))
  );
  if (images[frameIndex]) {
    renderImage(images[frameIndex]);
  }
}

// Tick loop (executed on requestAnimationFrame)
function tick() {
  // Interpolate current scroll progress toward target
  currentScrollProgress += (targetScrollProgress - currentScrollProgress) * ease;

  // Clean bounds limit
  if (currentScrollProgress < 0.0001) currentScrollProgress = 0;
  if (currentScrollProgress > 0.9999) currentScrollProgress = 1;

  // Find corresponding frame index
  const frameIndex = Math.min(
    frameCount - 1,
    Math.max(0, Math.floor(currentScrollProgress * (frameCount - 1)))
  );

  // Redraw canvas if frame changed or on initial update
  if (frameIndex !== lastRenderedFrame) {
    if (images[frameIndex] && images[frameIndex].complete) {
      renderImage(images[frameIndex]);
      lastRenderedFrame = frameIndex;
    }
  }

  // Fade out hero card and translate upwards as user scrolls past 30% of scroll-spacer height
  const fadeStart = 0.0;
  const fadeEnd = 0.3; // 30% of scroll spacer

  let heroOpacity = 1;
  let translateY = 0;

  if (currentScrollProgress >= fadeEnd) {
    heroOpacity = 0;
    translateY = -50;
  } else if (currentScrollProgress <= fadeStart) {
    heroOpacity = 1;
    translateY = 0;
  } else {
    const progress = (currentScrollProgress - fadeStart) / (fadeEnd - fadeStart);
    heroOpacity = 1 - progress;
    translateY = -progress * 50;
  }

  if (heroSection) {
    heroSection.style.opacity = heroOpacity;
    heroSection.style.transform = `translateY(${translateY}px)`;
  }

  // Scroll indicator fade out (disappears very early in scrolling)
  const indicatorOpacity = Math.max(0, 1 - (currentScrollProgress / 0.06));
  scrollIndicator.style.opacity = indicatorOpacity;

  requestAnimationFrame(tick);
}

// Initialize Application
async function init() {
  updateScrollProgress();
  
  // Preload and start animation
  await preloadImages();
  
  if (images[0]) {
    renderImage(images[0]);
  }
  
  // Bind events
  window.addEventListener("scroll", updateScrollProgress);
  window.addEventListener("resize", handleResize);
  
  // Trigger animation loop
  requestAnimationFrame(tick);
}

init();
