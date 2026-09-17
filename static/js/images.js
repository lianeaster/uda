/* Progressive image loading with blur-up effect */
(function () {
  if (!('IntersectionObserver' in window)) return;

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        var img = entry.target;
        var src = img.dataset.src || img.dataset.srcset;
        if (src) {
          if (img.dataset.srcset) {
            img.srcset = img.dataset.srcset;
          } else {
            img.src = img.dataset.src;
          }
        }
        img.addEventListener('load', function () {
          img.classList.add('loaded');
          var placeholder = img.nextElementSibling;
          if (placeholder && placeholder.classList.contains('img-placeholder')) {
            placeholder.classList.add('hidden');
          }
        }, { once: true });
        observer.unobserve(img);
      }
    });
  }, { rootMargin: '100px 0px', threshold: 0.01 });

  document.querySelectorAll('img[data-src], img[data-srcset]').forEach(function (img) {
    observer.observe(img);
  });

  // Immediate load for eager images
  document.querySelectorAll('img[loading="eager"]').forEach(function (img) {
    if (img.complete) {
      img.classList.add('loaded');
      var placeholder = img.nextElementSibling;
      if (placeholder && placeholder.classList.contains('img-placeholder')) {
        placeholder.classList.add('hidden');
      }
    } else {
      img.addEventListener('load', function () {
        img.classList.add('loaded');
        var placeholder = img.nextElementSibling;
        if (placeholder && placeholder.classList.contains('img-placeholder')) {
          placeholder.classList.add('hidden');
        }
      }, { once: true });
    }
  });
})();