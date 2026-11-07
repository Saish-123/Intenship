/*
 * Ridgeline Trail Club | Week 3 interactivity (plain JavaScript, no libraries)
 *
 * Structure
 *   1. Helpers        small utilities shared by every feature
 *   2. Features       one init function per feature, each independent
 *   3. Boot           runs every feature in a try/catch so one failure
 *                     cannot stop the others
 *
 * Features: theme, mobile nav, header/back-to-top state, scroll-spy,
 * scroll reveal, trail filter/search/sort, schedule (live dates + Reserve),
 * booking form with validation, photo lightbox, FAQ expand-all, footer year.
 *
 * Progressive enhancement: the page is fully usable without this file.
 * Everything here only adds to it.
 */
(function () {
  'use strict';
 
  /* ------------------------------------------------------------------ *
   * 1. HELPERS
   * ------------------------------------------------------------------ */
  const root = document.documentElement;
  const $ = (selector, scope) => (scope || document).querySelector(selector);
  const $$ = (selector, scope) => Array.from((scope || document).querySelectorAll(selector));
 
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const desktopNav = window.matchMedia('(min-width: 760px)');
 
  /* State shared between features. The schedule fills it, the form reads it. */
  const app = { hikes: [] };
 
  /* localStorage can throw (private mode, blocked cookies), so wrap it. */
  const storage = {
    get(key) { try { return window.localStorage.getItem(key); } catch { return null; } },
    set(key, value) { try { window.localStorage.setItem(key, value); } catch { /* ignore */ } }
  };
 
  /* Speak a message to screen readers through the polite live region. */
  function announce(message) {
    const region = $('#announcer');
    if (!region) { return; }
    region.textContent = '';
    window.setTimeout(function () { region.textContent = message; }, 60);
  }
 
  /* Run fn only after the user has stopped for `wait` ms (keeps typing smooth). */
  function debounce(fn, wait) {
    let timer;
    return function () {
      const args = arguments;
      window.clearTimeout(timer);
      timer = window.setTimeout(function () { fn.apply(null, args); }, wait);
    };
  }
 
  function scrollBehavior() { return reduceMotion.matches ? 'auto' : 'smooth'; }
 
  /* <dialog> helper: showModal where supported, plain open attribute otherwise. */
  function openDialog(dialog) {
    if (typeof dialog.showModal === 'function') { dialog.showModal(); } else { dialog.setAttribute('open', ''); }
  }
  function closeDialog(dialog) {
    if (typeof dialog.close === 'function') { dialog.close(); } else { dialog.removeAttribute('open'); }
  }
  /* Close on the Close/Done buttons and on a click outside the box. */
  function wireDialog(dialog) {
    dialog.addEventListener('click', function (event) {
      if (event.target.closest('[data-close]')) { closeDialog(dialog); return; }
      const box = dialog.getBoundingClientRect();
      const outside = event.clientX < box.left || event.clientX > box.right ||
                      event.clientY < box.top || event.clientY > box.bottom;
      if (outside && event.target === dialog) { closeDialog(dialog); }
    });
  }
 
  const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const pad = (n) => String(n).padStart(2, '0');
  const isoDate = (d) => d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
  const labelDate = (d) => DAYS[d.getDay()] + ' ' + d.getDate() + ' ' + MONTHS[d.getMonth()];
  const plural = (n, word) => n + ' ' + word + (n === 1 ? '' : 's');
 
  /* ------------------------------------------------------------------ *
   * 2. FEATURES
   * ------------------------------------------------------------------ */
 
  /* 2.1 Theme toggle: remembers the choice, otherwise follows the system. */
  function initTheme() {
    const button = $('#theme-toggle');
    if (!button) { return; }
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const current = () => root.getAttribute('data-theme') || (media.matches ? 'dark' : 'light');
 
    function apply(theme, remember) {
      root.setAttribute('data-theme', theme);
      button.setAttribute('aria-pressed', String(theme === 'dark'));
      if (remember) { storage.set('rl-theme', theme); }
    }
 
    apply(current(), false);
    button.addEventListener('click', function () {
      const next = current() === 'dark' ? 'light' : 'dark';
      apply(next, true);
      announce((next === 'dark' ? 'Dark' : 'Light') + ' mode on');
    });
    if (media.addEventListener) {
      media.addEventListener('change', function (event) {
        if (!storage.get('rl-theme')) { apply(event.matches ? 'dark' : 'light', false); }
      });
    }
  }
 
  /* 2.2 Mobile menu: aria-expanded, Escape, click-outside, auto-close on desktop. */
  function initNav() {
    const toggle = $('#nav-toggle');
    const nav = $('#primary-nav');
    if (!toggle || !nav) { return; }
    const isOpen = () => toggle.getAttribute('aria-expanded') === 'true';
 
    function setOpen(open, returnFocus) {
      toggle.setAttribute('aria-expanded', String(open));
      nav.classList.toggle('is-open', open);
      if (!open && returnFocus) { toggle.focus(); }
    }
 
    toggle.addEventListener('click', function () { setOpen(!isOpen()); });
    nav.addEventListener('click', function (event) { if (event.target.closest('a')) { setOpen(false); } });
    document.addEventListener('click', function (event) {
      if (isOpen() && !event.target.closest('.site-header')) { setOpen(false); }
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && isOpen()) { setOpen(false, true); }
    });
    desktopNav.addEventListener('change', function (event) { if (event.matches) { setOpen(false); } });
  }
 
  /* 2.3 Header shadow + back-to-top button. Uses IntersectionObserver on two
        invisible markers instead of a scroll listener, so nothing runs per scroll event. */
  function initScrollState() {
    const header = $('#site-header');
    const toTop = $('#to-top');
    if (!('IntersectionObserver' in window)) { return; }
 
    function marker(top, className) {
      const el = document.createElement('div');
      el.className = 'scroll-marker ' + className;
      el.style.top = top + 'px';
      el.setAttribute('aria-hidden', 'true');
      document.body.appendChild(el);
      return el;
    }
 
    if (header) {
      new IntersectionObserver(function (entries) {
        header.classList.toggle('is-scrolled', !entries[0].isIntersecting);
      }).observe(marker(24, 'scroll-marker--near'));
    }
    if (toTop) {
      new IntersectionObserver(function (entries) {
        toTop.classList.toggle('is-visible', !entries[0].isIntersecting);
      }).observe(marker(600, 'scroll-marker--far'));
      toTop.addEventListener('click', function () {
        window.scrollTo({ top: 0, behavior: scrollBehavior() });
        const logo = $('.logo');
        if (logo) { logo.focus({ preventScroll: true }); }
      });
    }
  }
 
  /* 2.4 Scroll-spy: marks the nav link of the section in the middle of the screen. */
  function initScrollSpy() {
    if (!('IntersectionObserver' in window)) { return; }
    const links = $$('.nav-list a[href^="#"]').filter((a) => a.getAttribute('href').length > 1);
    const byId = new Map();
    links.forEach(function (link) {
      const section = $(link.getAttribute('href'));
      if (section) { byId.set(section, link); }
    });
    if (!byId.size) { return; }
 
    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) { return; }
        links.forEach((link) => link.removeAttribute('aria-current'));
        const link = byId.get(entry.target);
        if (link) { link.setAttribute('aria-current', 'true'); }
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
 
    byId.forEach((link, section) => observer.observe(section));
    const hero = $('#top');
    if (hero) { observer.observe(hero); }   /* hero has no link, so it clears the highlight */
  }
 
  /* 2.5 Scroll reveal: fade/slide content in once. Skipped for reduced-motion users. */
  function initReveal() {
    if (reduceMotion.matches || !('IntersectionObserver' in window)) { return; }
    const targets = $$('.section-head, .toolbar, .trail-item, .table-wrap, .gallery-grid li, .faq-grid details, .join-intro, .join-form');
    if (!targets.length) { return; }
 
    root.classList.add('js-reveal');
    targets.forEach(function (el, index) {
      el.classList.add('reveal');
      if (el.matches('.trail-item, .gallery-grid li')) { el.style.transitionDelay = (index % 3) * 70 + 'ms'; }
    });
 
    const observer = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -4% 0px' });
    targets.forEach((el) => observer.observe(el));
  }
 
  /* 2.6 Trails: filter by level, live search, sort. Everything re-renders from one state object. */
  function initTrails() {
    const grid = $('.trail-grid');
    const tools = $('#trail-tools');
    if (!grid || !tools) { return; }
 
    const chipGroup = $('.chips', tools);
    const search = $('#trail-search');
    const sortSelect = $('#trail-sort');
    const count = $('#trail-count');
    const empty = $('#trail-empty');
    const state = { level: 'all', query: '', sort: 'default' };
 
    const trails = $$('.trail-item', grid).map(function (el, index) {
      return {
        el: el,
        order: index,
        name: el.dataset.name,
        levels: el.dataset.levels.split(' '),
        distance: Number(el.dataset.distance),
        climb: Number(el.dataset.climb),
        text: el.textContent.replace(/\s+/g, ' ').toLowerCase()
      };
    });
 
    const sorters = {
      'default': (a, b) => a.order - b.order,
      'distance-asc': (a, b) => a.distance - b.distance,
      'distance-desc': (a, b) => b.distance - a.distance,
      'climb-asc': (a, b) => a.climb - b.climb,
      'name': (a, b) => a.name.localeCompare(b.name)
    };
 
    function render() {
      const query = state.query.trim().toLowerCase();
      const matches = trails.filter(function (t) {
        return (state.level === 'all' || t.levels.indexOf(state.level) !== -1) &&
               (!query || t.text.indexOf(query) !== -1);
      });
      const shown = new Set(matches);
 
      trails.forEach((t) => { t.el.hidden = !shown.has(t); });
      matches.slice().sort(sorters[state.sort]).forEach((t) => grid.appendChild(t.el));
 
      const customised = state.level !== 'all' || query !== '' || state.sort !== 'default';
      grid.classList.toggle('is-custom', customised);
      empty.hidden = matches.length > 0;
 
      count.textContent = matches.length
        ? 'Showing ' + matches.length + ' of ' + trails.length + ' trails'
        : 'No trails found';
    }
 
    function reset() {
      state.level = 'all'; state.query = ''; state.sort = 'default';
      search.value = ''; sortSelect.value = 'default';
      setChip('all');
      render();
    }
 
    function setChip(level) {
      $$('.chip', chipGroup).forEach((chip) => chip.setAttribute('aria-pressed', String(chip.dataset.level === level)));
    }
 
    chipGroup.addEventListener('click', function (event) {
      const chip = event.target.closest('.chip');
      if (!chip) { return; }
      state.level = chip.dataset.level;
      setChip(state.level);
      render();
    });
    search.addEventListener('input', debounce(function () { state.query = search.value; render(); }, 150));
    sortSelect.addEventListener('change', function () { state.sort = sortSelect.value; render(); });
    document.addEventListener('click', function (event) {
      if (event.target.closest('[data-trail-reset]')) { reset(); search.focus(); }
    });
 
    render();
  }
 
  /* 2.7 Schedule: dates recalculated from today, spot badges, Reserve buttons. */
  function initSchedule() {
    const table = $('.schedule-table');
    if (!table) { return; }
    const rows = $$('tbody tr', table);
 
    /* The next Saturday on or after today, set to noon to dodge daylight-saving edges. */
    const today = new Date();
    today.setHours(12, 0, 0, 0);
    const firstSaturday = new Date(today);
    firstSaturday.setDate(today.getDate() + ((6 - today.getDay() + 7) % 7));
 
    function whenLabel(date) {
      const days = Math.round((date - today) / 86400000);
      if (days === 0) { return 'Today'; }
      if (days === 1) { return 'Tomorrow'; }
      return 'In ' + days + ' days';
    }
 
    function badgeFor(spots) {
      if (spots === 0) { return { text: 'Full', cls: 'badge--full' }; }
      if (spots <= 5) { return { text: 'Filling fast', cls: 'badge--warn' }; }
      return { text: 'Open', cls: 'badge--ok' };
    }
 
    /* Redraw one row from its data object. Called at start and after each booking. */
    function paintRow(hike) {
      const cell = $('td:nth-child(4)', hike.row);
      const badge = badgeFor(hike.spots);
      cell.innerHTML = '';
      const num = document.createElement('span');
      num.className = 'spots-num';
      num.textContent = hike.spots;
      const tag = document.createElement('span');
      tag.className = 'badge ' + badge.cls;
      tag.textContent = badge.text;
      cell.append(num, ' ', tag);
 
      const button = $('.reserve-btn', hike.row);
      if (button) {
        button.disabled = hike.spots === 0;
        button.textContent = hike.spots === 0 ? 'Full' : 'Reserve';
        button.setAttribute('aria-label', (hike.spots === 0 ? 'Full: ' : 'Reserve ') + hike.trail + ' on ' + hike.dateLabel);
      }
    }
 
    /* Build the hike list and write the live dates. */
    app.hikes = rows.map(function (row) {
      const date = new Date(firstSaturday);
      date.setDate(firstSaturday.getDate() + Number(row.dataset.offset));
      const hike = {
        id: row.dataset.id,
        trail: row.dataset.trail,
        spots: Number(row.dataset.spots),
        dateLabel: labelDate(date),
        iso: isoDate(date),
        row: row
      };
      const time = $('time', row);
      time.dateTime = hike.iso;
      time.textContent = hike.dateLabel;
      $('.when', row).textContent = whenLabel(date);
      return hike;
    });
 
    /* Add the Reserve column (header cell + one button per row). */
    const headRow = $('thead tr', table);
    const th = document.createElement('th');
    th.scope = 'col';
    th.textContent = 'Reserve';
    headRow.appendChild(th);
    app.hikes.forEach(function (hike) {
      const td = document.createElement('td');
      td.className = 'cell-action';
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn btn-small reserve-btn';
      button.dataset.id = hike.id;
      td.appendChild(button);
      hike.row.appendChild(td);
      paintRow(hike);
    });
 
    /* One listener for the whole table (event delegation). */
    table.addEventListener('click', function (event) {
      const button = event.target.closest('.reserve-btn');
      if (!button || button.disabled) { return; }
      document.dispatchEvent(new CustomEvent('hike:select', { detail: { id: button.dataset.id } }));
    });
 
    /* The form tells us when seats were booked. */
    document.addEventListener('hike:booked', function (event) {
      const hike = app.hikes.find((h) => h.id === event.detail.id);
      if (!hike) { return; }
      hike.spots = Math.max(0, hike.spots - event.detail.seats);
      paintRow(hike);
      hike.row.classList.add('row-flash');
      window.setTimeout(() => hike.row.classList.remove('row-flash'), 1600);
    });
  }
 
  /* 2.8 Booking form: validation, dependent dropdown, stepper, confirmation. */
  function initForm() {
    const form = $('#join-form');
    if (!form) { return; }
    const MAX_GROUP = 6;
    const f = {
      name: $('#name'), email: $('#email'), trail: $('#trail'),
      date: $('#hike-date'), group: $('#group'), consent: $('#consent')
    };
    const summary = $('#error-summary');
    const summaryTitle = $('#error-summary-title');
    const summaryList = $('#error-summary-list');
    const hint = $('#group-hint');
    const dialog = $('#confirm-dialog');
    const touched = new Set();
 
    const hikeById = (id) => app.hikes.find((h) => h.id === id);
    const selectedHike = () => hikeById(f.date.value);
    const maxGroup = () => { const h = selectedHike(); return h ? Math.min(MAX_GROUP, h.spots) : MAX_GROUP; };
 
    /* Each validator returns an error message, or '' when the field is fine. */
    const validators = {
      name() {
        const v = f.name.value.trim();
        if (!v) { return 'Please enter your name.'; }
        if (v.length < 2) { return 'Your name needs at least 2 characters.'; }
        return '';
      },
      email() {
        const v = f.email.value.trim();
        if (!v) { return 'Please enter your email address.'; }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v)) { return 'That email does not look right. Try name@example.com.'; }
        return '';
      },
      trail() { return f.trail.value ? '' : 'Please choose a trail.'; },
      date() {
        if (!f.trail.value) { return 'Choose a trail first, then a date.'; }
        return f.date.value ? '' : 'Please choose a date.';
      },
      group() {
        const n = Number(f.group.value);
        if (f.group.value === '' || !Number.isInteger(n)) { return 'Enter a whole number of people.'; }
        if (n < 1) { return 'At least 1 person is needed.'; }
        if (n > MAX_GROUP) { return 'Bookings are limited to ' + MAX_GROUP + ' people.'; }
        const hike = selectedHike();
        if (hike && n > hike.spots) { return 'Only ' + plural(hike.spots, 'spot') + ' left on that hike.'; }
        return '';
      },
      consent() { return f.consent.checked ? '' : 'Please confirm you have read the safety policy.'; }
    };
 
    function errorEl(key) { return $('#' + f[key].id + '-error'); }
 
    function showError(key, message) {
      const input = f[key];
      const el = errorEl(key);
      if (message) {
        el.textContent = message;
        el.hidden = false;
        input.setAttribute('aria-invalid', 'true');
      } else {
        el.hidden = true;
        el.textContent = '';
        input.removeAttribute('aria-invalid');
      }
    }
 
    function validateField(key) {
      const message = validators[key]();
      showError(key, message);
      return message;
    }
 
    /* Rebuild the Date list for the chosen trail from the live schedule data. */
    function populateDates(trail, keepId) {
      f.date.innerHTML = '';
      const add = (value, text, disabled) => {
        const option = document.createElement('option');
        option.value = value; option.textContent = text; option.disabled = !!disabled;
        f.date.appendChild(option);
      };
      if (!trail) { add('', 'Choose a trail first'); f.date.disabled = true; return; }
      add('', 'Choose a date');
      app.hikes.filter((h) => h.trail === trail).forEach(function (h) {
        add(h.id, h.dateLabel + (h.spots > 0 ? ' (' + plural(h.spots, 'spot') + ' left)' : ' (Full)'), h.spots === 0);
      });
      f.date.disabled = false;
      if (keepId) { f.date.value = keepId; }
    }
 
    function updateGroupLimits() {
      const max = maxGroup();
      f.group.max = String(max);
      const hike = selectedHike();
      hint.textContent = hike
        ? plural(hike.spots, 'spot') + ' left on this hike (up to ' + MAX_GROUP + ' per booking).'
        : 'Up to ' + MAX_GROUP + ' people per booking.';
      if (Number(f.group.value) > max && max >= 1) { f.group.value = String(max); }
    }
 
    function afterTrailOrDateChange() {
      updateGroupLimits();
      if (touched.has('group')) { validateField('group'); }
    }
 
    /* --- live validation: after a field has been visited, re-check as the user types --- */
    Object.keys(validators).forEach(function (key) {
      const input = f[key];
      input.addEventListener('blur', function () { touched.add(key); validateField(key); });
      const evt = (input.type === 'checkbox' || input.tagName === 'SELECT') ? 'change' : 'input';
      input.addEventListener(evt, function () { if (touched.has(key)) { validateField(key); } });
    });
 
    f.trail.addEventListener('change', function () {
      populateDates(f.trail.value);
      showError('date', '');
      touched.delete('date');
      afterTrailOrDateChange();
    });
    f.date.addEventListener('change', afterTrailOrDateChange);
 
    /* --- group size stepper (event delegation on the buttons) --- */
    form.addEventListener('click', function (event) {
      const btn = event.target.closest('.stepper-btn');
      if (!btn) { return; }
      const next = (Number(f.group.value) || 1) + Number(btn.dataset.step);
      f.group.value = String(Math.min(Math.max(next, 1), maxGroup()));
      touched.add('group');
      validateField('group');
    });
 
    /* --- error summary --- */
    function showSummary(errors) {
      summaryTitle.textContent = 'Please fix ' + plural(errors.length, 'problem') + ' before sending';
      summaryList.innerHTML = '';
      errors.forEach(function (item) {
        const li = document.createElement('li');
        const a = document.createElement('a');
        a.href = '#' + f[item.key].id;
        a.textContent = item.message;
        a.dataset.field = item.key;
        li.appendChild(a);
        summaryList.appendChild(li);
      });
      summary.hidden = false;
      summary.focus();
    }
    function hideSummary() { summary.hidden = true; summaryList.innerHTML = ''; }
    summaryList.addEventListener('click', function (event) {
      const link = event.target.closest('a[data-field]');
      if (!link) { return; }
      event.preventDefault();
      f[link.dataset.field].focus();
    });
 
    /* --- submit --- */
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      const errors = [];
      Object.keys(validators).forEach(function (key) {
        touched.add(key);
        const message = validateField(key);
        if (message) { errors.push({ key: key, message: message }); }
      });
      if (errors.length) {
        showSummary(errors);
        announce(plural(errors.length, 'problem') + ' to fix');
        return;
      }
      hideSummary();
 
      const hike = selectedHike();
      const seats = Number(f.group.value);
      const person = f.name.value.trim();
      const email = f.email.value.trim();
 
      document.dispatchEvent(new CustomEvent('hike:booked', { detail: { id: hike.id, seats: seats } }));
      $('#confirm-text').textContent = 'Thanks, ' + person + '. We have held ' + plural(seats, 'spot') +
        ' on ' + hike.trail + ' (' + hike.dateLabel + '). Meeting details are on their way to ' + email + '.';
      openDialog(dialog);
      announce('Booking requested for ' + hike.trail + ' on ' + hike.dateLabel);
 
      form.reset();
      touched.clear();
      Object.keys(f).forEach((key) => showError(key, ''));
      populateDates('');
      updateGroupLimits();
    });
 
    if (dialog) { wireDialog(dialog); }
 
    /* --- Reserve buttons in the schedule pre-fill this form --- */
    document.addEventListener('hike:select', function (event) {
      const hike = hikeById(event.detail.id);
      if (!hike) { return; }
      f.trail.value = hike.trail;
      populateDates(hike.trail, hike.id);
      showError('trail', ''); showError('date', '');
      updateGroupLimits();
      form.scrollIntoView({ behavior: scrollBehavior(), block: 'start' });
      (f.name.value ? f.group : f.name).focus({ preventScroll: true });
      announce(hike.trail + ' on ' + hike.dateLabel + ' selected. Fill in your details to finish.');
    });
 
    populateDates('');
    updateGroupLimits();
  }
 
  /* 2.9 Photo lightbox: opens a dialog, arrow keys + swipe to move between photos. */
  function initLightbox() {
    const dialog = $('#lightbox');
    const items = $$('.gallery-grid li');
    if (!dialog || !items.length) { return; }
    const view = $('#lightbox-img');
    const caption = $('#lightbox-caption');
    const counter = $('#lightbox-count');
    const photos = [];
    let index = 0;
 
    /* Wrap each image in a real button so mouse, touch and keyboard users can open it. */
    items.forEach(function (li, i) {
      const img = $('img', li);
      if (!img) { return; }
      photos.push({ src: img.getAttribute('src'), alt: img.alt });
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'gallery-btn';
      button.dataset.index = String(i);
      button.setAttribute('aria-label', 'View larger: ' + img.alt);
      img.replaceWith(button);
      button.appendChild(img);
    });
 
    function show(i) {
      index = (i + photos.length) % photos.length;
      view.src = photos[index].src;
      view.alt = photos[index].alt;
      caption.textContent = photos[index].alt;
      counter.textContent = 'Photo ' + (index + 1) + ' of ' + photos.length;
    }
 
    $('.gallery-grid').addEventListener('click', function (event) {
      const button = event.target.closest('.gallery-btn');
      if (!button) { return; }
      show(Number(button.dataset.index));
      openDialog(dialog);
    });
    $('#lightbox-prev').addEventListener('click', () => show(index - 1));
    $('#lightbox-next').addEventListener('click', () => show(index + 1));
    dialog.addEventListener('keydown', function (event) {
      if (event.key === 'ArrowLeft') { show(index - 1); }
      if (event.key === 'ArrowRight') { show(index + 1); }
    });
 
    let startX = null;
    dialog.addEventListener('touchstart', function (event) { startX = event.changedTouches[0].clientX; }, { passive: true });
    dialog.addEventListener('touchend', function (event) {
      if (startX === null) { return; }
      const dx = event.changedTouches[0].clientX - startX;
      if (Math.abs(dx) > 50) { show(index + (dx < 0 ? 1 : -1)); }
      startX = null;
    }, { passive: true });
 
    wireDialog(dialog);
  }
 
  /* 2.10 FAQ: expand or collapse every answer at once. */
  function initFaq() {
    const button = $('#faq-toggle');
    const items = $$('.faq-grid details');
    if (!button || !items.length) { return; }
    const allOpen = () => items.every((d) => d.open);
    const label = () => { button.textContent = allOpen() ? 'Collapse all' : 'Expand all'; };
 
    button.addEventListener('click', function () {
      const open = !allOpen();
      items.forEach((d) => { d.open = open; });
      label();
    });
    items.forEach((d) => d.addEventListener('toggle', label));
    label();
  }
 
  /* 2.11 Footer year stays correct without editing the file each January. */
  function initYear() {
    const el = $('#year');
    if (el) { el.textContent = String(new Date().getFullYear()); }
  }
 
  /* ------------------------------------------------------------------ *
   * 3. BOOT
   * Order matters: the schedule must run before the form so the hike
   * list exists when the form builds its Date dropdown.
   * ------------------------------------------------------------------ */
  const features = [initTheme, initNav, initScrollState, initScrollSpy, initReveal,
                    initTrails, initSchedule, initForm, initLightbox, initFaq, initYear];
 
  function boot() {
    features.forEach(function (feature) {
      try { feature(); } catch (error) { console.error('[Ridgeline] ' + feature.name + ' failed:', error); }
    });
  }
 
  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', boot); } else { boot(); }
})();
 