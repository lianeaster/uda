(function () {
  var els = Array.prototype.slice.call(document.querySelectorAll('[data-reveal]'));
  if (!els.length) return;

  if (!('IntersectionObserver' in window)) {
    els.forEach(function (el) { el.classList.add('is-revealed'); });
    return;
  }

  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        var el = entry.target;
        var delay = parseInt(el.dataset.revealDelay, 10) || 0;
        
        if (prefersReducedMotion) {
          el.classList.add('is-revealed');
        } else {
          setTimeout(function () {
            el.classList.add('is-revealed');
            
            // Trigger counter animation for hero stats
            if (el.classList.contains('hero-stats')) {
              animateCounters(el);
            }
            
            // Trigger marquee pause state
            if (el.classList.contains('partner-marquee')) {
              el.style.animationPlayState = 'running';
            }
          }, delay);
        }
        
        observer.unobserve(el);
      }
    });
  }, { rootMargin: '0px 0px -10% 0px', threshold: 0.1 });

  // Stagger delays for grid items
  var grids = document.querySelectorAll('.grid-cards, .card-grid, .partner-grid-static');
  grids.forEach(function (grid) {
    var items = grid.querySelectorAll('[data-reveal]');
    items.forEach(function (item, index) {
      item.style.transitionDelay = (index * 80) + 'ms';
    });
  });

  // Hero stats stagger
  var heroStats = document.querySelector('.hero-stats');
  if (heroStats) {
    var statItems = heroStats.querySelectorAll('.hero-stat');
    statItems.forEach(function (item, index) {
      item.style.transitionDelay = (index * 120) + 'ms';
    });
  }

  els.forEach(function (el) {
    if (el.getBoundingClientRect().top < window.innerHeight * 0.95) {
      el.classList.add('is-revealed');
    } else {
      observer.observe(el);
    }
  });

  // Animated counter function
  function animateCounters(container) {
    var counters = container.querySelectorAll('.stat-number');
    counters.forEach(function (counter) {
      var target = parseInt(counter.textContent.replace(/[^\d]/g, ''), 10);
      if (isNaN(target)) return;
      
      var suffix = counter.textContent.replace(/[\d,\s]/g, '');
      var duration = 1800;
      var start = 0;
      var startTime = null;
      
      function step(timestamp) {
        if (!startTime) startTime = timestamp;
        var progress = Math.min((timestamp - startTime) / duration, 1);
        var eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
        var current = Math.floor(target * eased);
        counter.textContent = current.toLocaleString() + suffix;
        
        if (progress < 1) {
          requestAnimationFrame(step);
        } else {
          counter.textContent = target.toLocaleString() + suffix;
        }
      }
      
      requestAnimationFrame(step);
    });
    
    // Animate the stat bars
    var statBars = container.querySelectorAll('.hero-stat::before');
    container.classList.add('is-visible');
  }
})();