(() => {
  const init = () => {
    const shell = document.querySelector('.graph-shell');
    const resizer = document.querySelector('.panel-resizer');
    if (!shell || !resizer || resizer.dataset.initialized) return;

    const saved = localStorage.getItem('cgmes-sidebar-width');
    if (saved) shell.style.setProperty('--sidebar-width', `${saved}px`);

    let resizing = false;

    resizer.addEventListener('pointerdown', (event) => {
      resizing = true;
      resizer.setPointerCapture(event.pointerId);
      shell.classList.add('is-resizing');
      event.preventDefault();
    });

    resizer.addEventListener('pointermove', (event) => {
      if (!resizing) return;
      const min = 260;
      const max = Math.max(min, window.innerWidth * 0.7);
      const width = Math.round(Math.min(max, Math.max(min, event.clientX)));
      shell.style.setProperty('--sidebar-width', `${width}px`);
      // Cytoscape recalculates its viewport on a window resize event.
      window.dispatchEvent(new Event('resize'));
    });

    const stop = (event) => {
      if (!resizing) return;
      resizing = false;
      if (event.pointerId !== undefined && resizer.hasPointerCapture(event.pointerId)) {
        resizer.releasePointerCapture(event.pointerId);
      }
      shell.classList.remove('is-resizing');
      localStorage.setItem(
        'cgmes-sidebar-width',
        getComputedStyle(shell).getPropertyValue('--sidebar-width').trim().replace('px', '')
      );
    };

    resizer.addEventListener('pointerup', stop);
    resizer.addEventListener('pointercancel', stop);
    resizer.dataset.initialized = 'true';
  };

  new MutationObserver(init).observe(document.body, { childList: true, subtree: true });
  init();
})();
