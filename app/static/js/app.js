// Kiosk dashboard: live queue, serve flow, route preview and ticket issue.
// All dynamic text is inserted with textContent (never innerHTML) to prevent XSS.
(function () {
  const POLL_MS = 5000;
  const boot = JSON.parse(document.getElementById('boot').textContent);
  const $ = (selector) => document.querySelector(selector);

  const els = {
    form: $('#enqueueForm'), serveBtn: $('#serveButton'), refreshBtn: $('#refreshBtn'),
    cards: $('#cardsGrid'), status: $('#queueStatus'),
    priorityCount: $('#priorityCount'), regularCount: $('#regularCount'),
    nextName: $('#nextName'), nextType: $('#nextType'),
    servingBox: $('#servingBox'), servingList: $('#servingList'),
    modal: $('#assignModal'), assignForm: $('#assignForm'),
    assignName: $('#assignName'), assignType: $('#assignType'),
    start: $('#assignStart'), destination: $('#assignDestination'),
    trains: $('#trainOptions'), preview: $('#routePreview'),
    submit: $('#assignSubmit'), cancel: $('#assignCancel'), result: $('#assignResult'),
  };

  let current = null;       // passenger being served in the modal
  let assigned = false;     // ticket already issued for `current`
  let previewSeq = 0;       // guards against out-of-order preview responses

  // ---------- helpers ----------
  function h(tag, props = {}, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(props)) {
      if (key === 'class') node.className = value;
      else if (key === 'text') node.textContent = value;
      else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value);
    }
    children.flat().forEach((c) => c != null && node.append(c));
    return node;
  }
  const fmtTime = (iso) => (iso ? new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—');
  const setStatus = (message, isError = false) => {
    els.status.textContent = message || '';
    els.status.style.color = isError ? '#8a1c28' : '';
  };

  // ---------- queue rendering ----------
  function renderCards(data) {
    const waiting = [...data.priority_q, ...data.regular_q];
    els.cards.replaceChildren();
    if (!waiting.length) {
      els.cards.append(h('p', { class: 'empty', text: 'Queue is empty. Waiting for commuters…' }));
    }
    waiting.forEach((p, index) => {
      const isPriority = p.lane === 'priority';
      const isNext = data.next && data.next.id === p.id;
      const card = h('article', { class: `card ${isPriority ? 'card--priority' : ''} ${isNext ? 'card--next' : ''}`.trim() },
        h('div', { class: 'card__head' },
          h('div', { class: 'card__name', text: `${index + 1}. ${p.name}` }),
          h('span', { class: `badge badge--${p.lane}`, text: p.type_label })),
        h('div', { class: 'card__meta', text: `Arrived ${fmtTime(p.arrival_time)}${isNext ? ' · next up' : ''}` }),
        h('div', { class: 'card__actions' },
          h('button', { type: 'button', class: 'btn btn--ghost', text: 'Remove', onclick: () => removePassenger(p) })));
      els.cards.append(card);
    });

    els.priorityCount.textContent = data.priority_q.length;
    els.regularCount.textContent = data.regular_q.length;
    els.nextName.textContent = data.next ? data.next.name : '—';
    els.nextType.textContent = data.next ? `(${data.next.type_label})` : '';
    els.serveBtn.disabled = !data.next;
  }

  function renderServing(list) {
    els.servingBox.hidden = list.length === 0;
    els.servingList.replaceChildren(...list.map((p) =>
      h('li', {},
        h('span', { class: 'grow', text: `${p.name} (${p.type_label})` }),
        h('button', { type: 'button', class: 'btn btn--primary', text: 'Resume', onclick: () => openModal(p) }),
        h('button', { type: 'button', class: 'btn btn--ghost', text: 'Return to queue', onclick: () => returnToQueue(p) }))));
  }

  async function refresh() {
    try {
      const data = await Api.get('/api/queues');
      renderCards(data);
      renderServing(data.serving);
      setStatus('');
    } catch (err) {
      setStatus(err.message, true);
    }
  }

  // ---------- queue actions ----------
  async function removePassenger(p) {
    if (!confirm(`Remove ${p.name} from the queue?`)) return;
    try { await Api.post('/api/remove', { id: p.id }); } catch (err) { alert(err.message); }
    refresh();
  }

  async function returnToQueue(p) {
    try { await Api.post('/api/return', { id: p.id }); } catch (err) { alert(err.message); }
    refresh();
  }

  els.form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const name = els.form.querySelector('#name').value.trim();
    const p_type = els.form.querySelector('#p_type').value;
    if (!name) return;
    try {
      await Api.post('/api/enqueue', { name, p_type });
      els.form.reset();
      els.form.querySelector('#name').focus();
      refresh();
    } catch (err) {
      alert(err.message);
    }
  });

  els.serveBtn.addEventListener('click', async () => {
    els.serveBtn.disabled = true;
    try {
      const { passenger } = await Api.post('/api/serve');
      await refresh();
      openModal(passenger);
    } catch (err) {
      alert(err.message);
      refresh();
    }
  });
  els.refreshBtn.addEventListener('click', refresh);

  // ---------- assign modal ----------
  function fillStations() {
    els.start.replaceChildren(...boot.stations.map((s) => h('option', { value: s, text: s })));
    els.start.value = boot.defaultStart;
    els.destination.replaceChildren(
      h('option', { value: '', text: '-- Select destination --' }),
      ...boot.stations.map((s) => h('option', { value: s, text: s })));
  }

  function setPreview(message, isError = false) {
    els.preview.textContent = message;
    els.preview.classList.toggle('route-preview--error', isError);
  }

  function renderTrains(trains) {
    els.trains.replaceChildren(...trains.map((t, i) =>
      h('label', { class: 'train-option' },
        h('input', { type: 'radio', name: 'train_number', value: t.train_number, ...(i === 0 ? { checked: '' } : {}) }),
        h('span', { text: `${t.train_number} — arrives in ${t.display}` }))));
  }

  async function updatePreview() {
    const seq = ++previewSeq;
    els.submit.disabled = true;
    if (!els.destination.value) {
      setPreview('No route calculated yet.');
      els.trains.replaceChildren(h('span', { class: 'muted', text: 'Pick a destination to see trains.' }));
      return;
    }
    try {
      const qs = new URLSearchParams({ start: els.start.value, destination: els.destination.value });
      const r = await Api.get(`/api/route?${qs}`);
      if (seq !== previewSeq) return;
      setPreview(`${r.train_line}: ${r.route_path_str} · ${r.total_time} min · ₱${r.fare}`);
      renderTrains(r.trains);
      els.submit.disabled = assigned;
    } catch (err) {
      if (seq !== previewSeq) return;
      setPreview(err.message, true);
      els.trains.replaceChildren();
    }
  }

  function openModal(passenger) {
    current = passenger;
    assigned = false;
    fillStations();
    els.assignName.textContent = passenger.name;
    els.assignType.textContent = passenger.type_label;
    els.result.hidden = true;
    els.result.replaceChildren();
    els.assignForm.hidden = false;
    els.cancel.textContent = 'Cancel (return to queue)';
    setPreview('No route calculated yet.');
    els.trains.replaceChildren(h('span', { class: 'muted', text: 'Pick a destination to see trains.' }));
    els.submit.disabled = true;
    els.modal.hidden = false;
    els.destination.focus();
  }

  function closeModal() {
    els.modal.hidden = true;
    current = null;
    refresh();
  }

  els.start.addEventListener('change', updatePreview);
  els.destination.addEventListener('change', updatePreview);

  els.cancel.addEventListener('click', async () => {
    if (current && !assigned) {
      try { await Api.post('/api/return', { id: current.id }); } catch (err) { alert(err.message); }
    }
    closeModal();
  });

  // Escape just hides the dialog; the passenger stays listed under "In service" and can be resumed.
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !els.modal.hidden) closeModal();
  });

  els.assignForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!current || assigned) return;
    els.submit.disabled = true;
    const train = els.assignForm.querySelector('input[name="train_number"]:checked');
    try {
      const r = await Api.post('/api/assign', {
        passenger_id: current.id,
        start_station: els.start.value,
        destination: els.destination.value,
        train_number: train ? train.value : null,
      });
      assigned = true;
      els.assignForm.hidden = true;
      els.result.hidden = false;
      els.result.replaceChildren(
        h('div', { class: 'ticket-result' },
          h('div', { text: `Ticket issued for ${current.name}` }),
          h('div', { text: `${r.train_line} · ${r.train_number}` }),
          h('div', { text: `${r.route_path_str} (${r.total_time} min)` }),
          h('div', { text: `Fare: ₱${r.fare}` }),
          h('div', { class: 'modal__actions' },
            h('a', { class: 'btn btn--primary', href: r.ticket_url, target: '_blank', rel: 'noopener', text: 'Print ticket' }),
            h('button', { type: 'button', class: 'btn btn--ghost', text: 'Close', onclick: closeModal }))));
      refresh();
    } catch (err) {
      els.submit.disabled = false;
      setPreview(err.message, true);
    }
  });

  // ---------- start ----------
  refresh();
  setInterval(() => { if (!document.hidden) refresh(); }, POLL_MS);
})();
