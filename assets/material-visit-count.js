(() => {
  const material = document.currentScript?.dataset.material;
  if (!material || document.querySelector('science-portal-visit-count')) return;

  const container = document.createElement('science-portal-visit-count');
  const root = container.attachShadow({ mode: 'open' });
  root.innerHTML = `
    <style>
      :host { display:block; clear:both; width:100%; }
      p { margin:0; padding:12px; background:#171f1c; color:#f1efe4;
        text-align:center; font:600 13px/1.5 system-ui,sans-serif; }
      strong { margin-inline-start:6px; font-size:17px; font-variant-numeric:tabular-nums; }
      @media print { :host { display:none; } }
    </style>
    <p>累計到訪<strong>—</strong></p>`;
  document.body.append(container);

  fetch('https://science-portal-visitor-counter.prayer168-science-portal.workers.dev/material-visits', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ materials: [material] }),
    signal: AbortSignal.timeout(8000)
  }).then(response => {
    if (!response.ok) throw new Error('Visit count unavailable');
    return response.json();
  }).then(([entry]) => {
    if (entry?.material === material && Number.isSafeInteger(entry.count) && entry.count >= 0) {
      root.querySelector('strong').textContent = new Intl.NumberFormat('zh-TW').format(entry.count);
    }
  }).catch(() => {
    root.querySelector('strong').title = '暫時無法取得統計';
  });
})();
