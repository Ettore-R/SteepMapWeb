/**
 * featured-modal.js — the "Featured tours" picker, shared by the website and the
 * featured tour pages.
 *
 * Any element with [data-open-featured] opens a clean list of the featured tours
 * (picture + name) with a search box. The list is read from /featured/tours.json,
 * in the page's current language (<html lang>). Tapping a tour opens its page.
 */
(function () {
  if (window.__featModal) return;
  window.__featModal = true;

  var DATA = null, loading = false, lastFocus = null;
  var back, title, search, list, empty, closeBtn;

  function lang() {
    return ((document.documentElement.lang || 'en').slice(0, 2)).toLowerCase();
  }
  function labels() {
    var all = (DATA && DATA.labels) || {};
    return all[lang()] || all.en || { title: 'Featured tours', search: 'Search', no_results: 'No tours found' };
  }
  function tours() {
    var all = (DATA && DATA.tours) || {};
    return all[lang()] || all.en || [];
  }
  // Ignore accents and case, so "zuckerhutl" also finds "Zuckerhütl".
  function norm(s) {
    return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  }

  function render() {
    var term = norm(search.value.trim());
    var n = 0;
    list.innerHTML = '';
    tours().forEach(function (t) {
      if (term && norm(t.title).indexOf(term) < 0) return;
      n++;
      var li = document.createElement('li');
      var a = document.createElement('a');
      a.href = t.url;
      var img = document.createElement('img');
      img.src = t.photo; img.alt = ''; img.loading = 'lazy';
      var sp = document.createElement('span');
      sp.textContent = t.title;
      a.appendChild(img); a.appendChild(sp); li.appendChild(a); list.appendChild(li);
    });
    empty.hidden = n > 0;
    empty.textContent = labels().no_results;
  }

  function build() {
    back = document.createElement('div');
    back.className = 'feat-back';
    back.id = 'featModal';
    back.setAttribute('role', 'dialog');
    back.setAttribute('aria-modal', 'true');
    back.innerHTML =
      '<div class="feat-modal">' +
      '<button class="feat-x" type="button" aria-label="Close">&times;</button>' +
      '<h3 class="feat-title"></h3>' +
      '<input class="feat-search" type="search" autocomplete="off" aria-label="Search">' +
      '<ul class="feat-list"></ul>' +
      '<p class="feat-empty" hidden></p>' +
      '</div>';
    document.body.appendChild(back);
    title = back.querySelector('.feat-title');
    search = back.querySelector('.feat-search');
    list = back.querySelector('.feat-list');
    empty = back.querySelector('.feat-empty');
    closeBtn = back.querySelector('.feat-x');

    search.addEventListener('input', render);
    closeBtn.addEventListener('click', close);
    back.addEventListener('click', function (e) { if (e.target === back) close(); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && back.classList.contains('open')) close();
    });
  }

  function loadData(cb) {
    if (DATA) return cb();
    if (loading) return;
    loading = true;
    fetch('/featured/tours.json', { cache: 'no-cache' })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (d) { DATA = d; loading = false; cb(); })
      .catch(function () { loading = false; cb(); });
  }

  function open() {
    if (!back) build();
    lastFocus = document.activeElement;
    title.textContent = labels().title;
    search.placeholder = labels().search;
    search.value = '';
    back.classList.add('open');
    document.body.style.overflow = 'hidden';
    loadData(render);
    render();
  }

  function close() {
    if (!back) return;
    back.classList.remove('open');
    document.body.style.overflow = '';
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  document.addEventListener('click', function (e) {
    var el = e.target && e.target.closest ? e.target.closest('[data-open-featured]') : null;
    if (!el) return;
    e.preventDefault();
    open();
  });

  // Tapping a tour in the list: stop the current page's still-pending loads first
  // (e.g. the home page's images and map tiles), so they don't stall the new page.
  document.addEventListener('click', function (e) {
    var a = e.target && e.target.closest ? e.target.closest('.feat-list a') : null;
    if (a) window.stop();
  });
})();
