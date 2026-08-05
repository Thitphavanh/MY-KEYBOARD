/* MY KEYBOARD — search bar: recent history + live product suggestions */

var SEARCH_HISTORY_KEY = "nb_search_history";
var SEARCH_HISTORY_MAX = 8;
var __searchDebounce = null;

function getSearchHistory() {
  try {
    var raw = localStorage.getItem(SEARCH_HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) { return []; }
}

function saveSearchHistory(term) {
  term = (term || "").trim();
  if (!term) return;
  try {
    var history = getSearchHistory().filter(function (t) { return t.toLowerCase() !== term.toLowerCase(); });
    history.unshift(term);
    localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(history.slice(0, SEARCH_HISTORY_MAX)));
  } catch (e) {}
}

function clearSearchHistory() {
  try { localStorage.removeItem(SEARCH_HISTORY_KEY); } catch (e) {}
}

function escapeHtml(str) {
  var div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function renderSearchHistory(panel) {
  var history = getSearchHistory();
  if (!history.length) {
    panel.classList.remove("show");
    panel.innerHTML = "";
    return;
  }
  panel.innerHTML =
    '<div class="suggest-head"><span data-i18n="recent_searches"></span><button type="button" class="search-clear-btn" data-i18n="clear_all"></button></div>' +
    '<div class="suggest-chips">' + history.map(function (term) {
      return '<button type="button" class="suggest-chip" data-term="' + escapeHtml(term) + '"><span class="ic sm" data-ic="clock"></span>' + escapeHtml(term) + "</button>";
    }).join("") + "</div>";
  applyI18n();
  fillIcons(panel);
  panel.classList.add("show");
}

function renderSearchResults(panel, products) {
  if (!products.length) {
    panel.innerHTML = '<div class="suggest-empty" data-i18n="no_results"></div>';
    applyI18n();
    panel.classList.add("show");
    return;
  }
  panel.innerHTML = '<div class="suggest-group">' + products.map(function (p) {
    var price = "₭ " + Number(p.price).toLocaleString();
    return '<a href="' + p.url + '" class="suggest-item"><span class="ic sm" data-ic="search"></span><span style="flex:1;">' + escapeHtml(p.name) + '</span><span style="color:var(--text-faint); font-size:11.5px;">' + price + "</span></a>";
  }).join("") + "</div>";
  fillIcons(panel);
  panel.classList.add("show");
}

function fetchSearchSuggestions(panel, query) {
  fetch("/api/search-suggest/?q=" + encodeURIComponent(query))
    .then(function (r) { return r.json(); })
    .then(function (data) { renderSearchResults(panel, data.results || []); })
    .catch(function () {});
}

function setupSearchSuggest(formEl) {
  var input = formEl.querySelector('input[name="search"]');
  var panel = formEl.querySelector(".search-suggest");
  if (!input || !panel) return;

  input.addEventListener("focus", function () {
    var q = input.value.trim();
    if (q.length >= 2) fetchSearchSuggestions(panel, q);
    else renderSearchHistory(panel);
  });

  input.addEventListener("input", function () {
    var q = input.value.trim();
    clearTimeout(__searchDebounce);
    if (q.length < 2) {
      renderSearchHistory(panel);
      return;
    }
    __searchDebounce = setTimeout(function () { fetchSearchSuggestions(panel, q); }, 220);
  });

  panel.addEventListener("click", function (e) {
    var chip = e.target.closest(".suggest-chip");
    if (chip) {
      input.value = chip.dataset.term;
      formEl.submit();
      return;
    }
    var clearBtn = e.target.closest(".search-clear-btn");
    if (clearBtn) {
      e.preventDefault();
      clearSearchHistory();
      renderSearchHistory(panel);
    }
  });

  formEl.addEventListener("submit", function () {
    saveSearchHistory(input.value);
  });
}

function initSearchSuggest() {
  document.querySelectorAll("form.nav-search, form.mobile-search-row").forEach(setupSearchSuggest);
  document.addEventListener("click", function (e) {
    if (!e.target.closest(".nav-search") && !e.target.closest(".mobile-search-row")) {
      document.querySelectorAll(".search-suggest").forEach(function (p) { p.classList.remove("show"); });
    }
  });
}
