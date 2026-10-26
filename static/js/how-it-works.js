const figures = document.querySelectorAll('.hiw');

// Size each reveal clip to the real rendered text, so nothing gets trimmed
// and the wipe edge tracks the text regardless of the monospace font metrics.
const fitClips = () => {
  figures.forEach((fig) => {
    const oldText = fig.querySelector('.hiw-line-old');
    const newText = fig.querySelector('.hiw-new-inner .hiw-line');
    const delRect = fig.querySelector('.hiw-del-rect');
    const typRect = fig.querySelector('.hiw-typ-rect');
    try {
      if (oldText instanceof SVGTextElement && delRect) {
        delRect.setAttribute('width', String(Math.ceil(oldText.getComputedTextLength()) + 8));
      }
      if (newText instanceof SVGTextElement && typRect) {
        typRect.setAttribute('width', String(Math.ceil(newText.getComputedTextLength()) + 8));
      }
    } catch (e) {}
  });
};

fitClips();
if (document.fonts && document.fonts.ready) document.fonts.ready.then(fitClips);
window.addEventListener('resize', fitClips);

if (figures.length && 'IntersectionObserver' in window) {
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        entry.target.classList.toggle('hiw-paused', !entry.isIntersecting);
      }
    },
    { rootMargin: '80px' },
  );
  figures.forEach((figure) => observer.observe(figure));
}
