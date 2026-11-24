// Reports page: tabs, filtering, timezone display, live clock, clear logs.
document.addEventListener('DOMContentLoaded', () => {
  const $ = (selector) => document.querySelector(selector);

  // ----- tabs -----
  const tabs = document.querySelectorAll('.tab');
  const panels = document.querySelectorAll('.tab-content');
  tabs.forEach((tab) => tab.addEventListener('click', () => {
    tabs.forEach((t) => { t.classList.toggle('active', t === tab); t.setAttribute('aria-selected', t === tab); });
    panels.forEach((p) => p.classList.toggle('active', p.id === tab.dataset.tab));
  }));

  // ----- filters -----
  const filterType = $('#filterType');
  const filterTrain = $('#filterTrain');
  const search = $('#searchLogs');
  const body = $('#logsTableBody');
  const counter = $('#recordCount');

  function applyFilters() {
    if (!body) return;
    const lane = filterType.value;
    const line = filterTrain.value;
    const q = search.value.trim().toLowerCase();
    let visible = 0;
    body.querySelectorAll('tr').forEach((row) => {
      const matches =
        (lane === 'all' || row.dataset.lane === lane) &&
        (line === 'all' || row.dataset.train === line) &&
        (!q || row.dataset.name.toLowerCase().includes(q) || row.dataset.destination.toLowerCase().includes(q));
      row.hidden = !matches;
      if (matches) visible += 1;
    });
    if (counter) counter.textContent = visible;
  }
  [filterType, filterTrain].forEach((el) => el.addEventListener('change', applyFilters));
  search.addEventListener('input', applyFilters);

  // ----- timezone display -----
  const tzMode = $('#tzMode');
  function renderTimes() {
    if (!body) return;
    body.querySelectorAll('tr').forEach((row) => {
      const cell = row.querySelector('.tsDisplay');
      const date = new Date(Number(row.dataset.tsEpoch) * 1000);
      if (!cell.dataset.server) cell.dataset.server = cell.textContent;
      if (tzMode.value === 'server') cell.textContent = cell.dataset.server;
      else if (tzMode.value === 'utc') cell.textContent = `${date.toISOString().replace('T', ' ').slice(0, 19)} UTC`;
      else cell.textContent = date.toLocaleString();
    });
  }
  tzMode.addEventListener('change', renderTimes);

  // ----- live clock -----
  const clock = $('#liveClock');
  if (clock) {
    const tick = () => { clock.textContent = new Date().toLocaleTimeString('en-GB'); };
    tick();
    setInterval(tick, 1000);
  }

  // ----- clear logs (admin) -----
  $('#clearLogs').addEventListener('click', async () => {
    if (!confirm('Clear ALL transaction logs? This cannot be undone.')) return;
    try {
      await Api.post('/reports/clear');
      location.reload();
    } catch (err) {
      alert(err.message);
    }
  });
});
