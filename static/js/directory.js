const list = document.getElementById('list');
const status = document.getElementById('status');
const search = document.getElementById('search');
const sort = document.getElementById('sort');
const noResults = document.getElementById('no-results');

if (list && search && sort && status) {
  const items = Array.from(list.querySelectorAll('li[data-name]'));
  const total = items.length;

  const sortItems = (values) => {
    const sorted = [...values];
    const byName = (a, b) => a.dataset.name.localeCompare(b.dataset.name);
    const byDate = (a, b) => (Date.parse(a.dataset.date) || 0) - (Date.parse(b.dataset.date) || 0);
    if (sort.value === 'az') sorted.sort(byName);
    else if (sort.value === 'za') sorted.sort((a, b) => byName(b, a));
    else if (sort.value === 'new') sorted.sort((a, b) => byDate(b, a));
    else if (sort.value === 'old') sorted.sort(byDate);
    return sorted;
  };

  const syncUrl = () => {
    const params = new URLSearchParams();
    if (search.value.trim()) params.set('q', search.value.trim());
    if (sort.value !== 'new') params.set('sort', sort.value);
    const query = params.toString();
    history.replaceState(null, '', query ? `?${query}` : location.pathname);
  };

  const update = () => {
    const query = search.value.trim().toLowerCase();
    const matches = items.filter(
      (item) =>
        !query ||
        (item.dataset.name || '').includes(query) ||
        (item.dataset.github || '').includes(query),
    );
    const ordered = sortItems(matches);

    for (const item of items) item.hidden = true;
    for (const item of ordered) {
      item.hidden = false;
      list.appendChild(item);
    }
    if (noResults) {
      list.appendChild(noResults);
      noResults.hidden = matches.length !== 0;
    }

    status.textContent = matches.length === total
      ? `${total} subdomain${total === 1 ? '' : 's'}.`
      : `${matches.length} of ${total} subdomains.`;
    if (!matches.length && query) status.textContent = `No subdomains match “${query}”.`;
    syncUrl();
  };

  const seed = new URLSearchParams(location.search);
  if (seed.get('q')) search.value = seed.get('q');
  if (seed.get('sort')) sort.value = seed.get('sort');

  let debounce;
  search.addEventListener('input', () => {
    window.clearTimeout(debounce);
    debounce = window.setTimeout(update, 120);
  });
  sort.addEventListener('change', update);
  document.getElementById('clear')?.addEventListener('click', () => {
    search.value = '';
    update();
    search.focus();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key !== '/' || event.metaKey || event.ctrlKey) return;
    const element = document.activeElement;
    const typing =
      element instanceof HTMLInputElement ||
      element instanceof HTMLTextAreaElement ||
      element instanceof HTMLSelectElement;
    if (typing) return;
    event.preventDefault();
    search.focus();
  });

  update();
}
