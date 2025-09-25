// Simple frontend i18n loader for EN/AR without backend changes
// - Uses localStorage key 'ui.lang' (default 'en')
// - Loads JSON from /static/core/i18n/{lang}.json
// - Replaces elements with [data-i18n]
// - Applies dir/language attributes and toggles rtl.css

(function () {
  var DEFAULT_LANG = 'en';
  var SUPPORTED = { en: 'ltr', ar: 'rtl' };

  function getLang() {
    try { return localStorage.getItem('ui.lang') || DEFAULT_LANG; } catch (e) { return DEFAULT_LANG; }
  }

  function setLang(lang) {
    try { localStorage.setItem('ui.lang', lang); } catch (e) {}
  }

  function loadJSON(url) {
    return fetch(url, { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : {}; }).catch(function () { return {}; });
  }

  function applyDir(lang) {
    var dir = SUPPORTED[lang] || 'ltr';
    var html = document.documentElement;
    html.setAttribute('lang', lang);
    // Keep navbar LTR; flip only content via class
    if (dir === 'rtl') {
      html.classList.add('rtl-ui');
    } else {
      html.classList.remove('rtl-ui');
    }
    // Toggle rtl stylesheet if present
    var linkId = 'rtl-stylesheet';
    var existing = document.getElementById(linkId);
    if (dir === 'rtl') {
      if (!existing) {
        var l = document.createElement('link');
        l.id = linkId;
        l.rel = 'stylesheet';
        l.href = (window.STATIC_URL || '/static/') + 'core/css/rtl.css';
        document.head.appendChild(l);
      }
    } else if (existing) {
      existing.parentNode.removeChild(existing);
    }
  }

  function resolveKey(dict, key) {
    if (!key) return '';
    var parts = key.split('.');
    var cur = dict;
    for (var i = 0; i < parts.length; i++) {
      if (cur && Object.prototype.hasOwnProperty.call(cur, parts[i])) {
        cur = cur[parts[i]];
      } else {
        return null;
      }
    }
    return typeof cur === 'string' ? cur : null;
  }

  function applyTranslations(dict) {
    var nodes = document.querySelectorAll('[data-i18n]');
    nodes.forEach(function (el) {
      var key = el.getAttribute('data-i18n');
      var val = resolveKey(dict, key);
      if (val == null) return; // fallback to existing text
      if (el.hasAttribute('data-i18n-html')) {
        el.innerHTML = val;
      } else {
        el.textContent = val;
      }
    });
    // Attributes
    var attrNodes = document.querySelectorAll('[data-i18n-attr]');
    attrNodes.forEach(function (el) {
      try {
        var map = JSON.parse(el.getAttribute('data-i18n-attr'));
        Object.keys(map || {}).forEach(function (attr) {
          var v = resolveKey(dict, map[attr]);
          if (v != null) el.setAttribute(attr, v);
        });
      } catch (e) {}
    });
    // Phrase sweep (bidirectional) and attribute replacements
    try {
      var lang = getLang();
      var base = (window.STATIC_URL || '/static/') + 'core/i18n/';
      Promise.all([
        loadJSON(base + 'phrases.en.json'),
        loadJSON(base + 'phrases.ar.json'),
        loadJSON(base + 'lexicon.' + (lang === 'ar' ? 'ar' : 'en') + '.json')
      ]).then(function (arr) {
        var phrEn = arr[0] || {};
        var phrAr = arr[1] || {};
        var lex = arr[2] || {};

        var pairs = [];
        if (lang === 'ar') {
          Object.keys(phrEn).forEach(function (k) {
            if (typeof phrEn[k] !== 'string') return;
            var tgt = phrAr[k];
            if (typeof tgt === 'string') pairs.push({ from: k, to: tgt });
          });
        } else {
          Object.keys(phrAr).forEach(function (k) {
            if (typeof phrAr[k] !== 'string') return;
            var tgt = phrEn[k];
            if (typeof tgt === 'string') pairs.push({ from: phrAr[k], to: tgt });
          });
        }

        // Sort by length desc to avoid partial overlaps
        pairs.sort(function(a,b){ return b.from.length - a.from.length; });

        function ciReplace(text, from, to) {
          try {
            var re = new RegExp(from.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
            return text.replace(re, to);
          } catch (e) { return text; }
        }

        // Text nodes
        var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
        var node;
        while ((node = walker.nextNode())) {
          var text = node.nodeValue;
          if (!text || !text.trim()) continue;
          var replaced = text;
          pairs.forEach(function (p) { replaced = ciReplace(replaced, p.from, p.to); });
          // Lexicon per-word (simple word boundaries for latin; direct replace otherwise)
          Object.keys(lex).forEach(function (w) {
            var to = lex[w];
            // if latin word, use \b boundaries; else direct
            if (/^[A-Za-z][A-Za-z\- ]*$/.test(w)) {
              try { replaced = replaced.replace(new RegExp('\\b' + w + '\\b', 'gi'), to); } catch (e) {}
            } else {
              replaced = replaced.split(w).join(to);
            }
          });
          if (replaced !== text) node.nodeValue = replaced;
        }

        // Attribute replacements
        ['placeholder','title','aria-label','value'].forEach(function(attr){
          document.querySelectorAll('['+attr+']').forEach(function(el){
            // Never touch CSRF token fields
            if (attr === 'value') {
              var nameAttr = (el.getAttribute('name') || '').toLowerCase();
              if (nameAttr === 'csrfmiddlewaretoken' || nameAttr.indexOf('csrf') !== -1) {
                return;
              }
            }
            var cur = el.getAttribute(attr);
            if (!cur) return;
            var newVal = cur;
            pairs.forEach(function(p){ newVal = ciReplace(newVal, p.from, p.to); });
            Object.keys(lex).forEach(function (w) {
              var to = lex[w];
              if (/^[A-Za-z][A-Za-z\- ]*$/.test(w)) {
                try { newVal = newVal.replace(new RegExp('\\b' + w + '\\b', 'gi'), to); } catch (e) {}
              } else {
                newVal = newVal.split(w).join(to);
              }
            });
            if (newVal !== cur) el.setAttribute(attr, newVal);
          });
        });
      });
    } catch (e) { /* ignore */ }
  }

  function initSwitcher(lang, dict) {
    document.querySelectorAll('[data-lang-select]')
      .forEach(function (btn) {
        btn.addEventListener('click', function (e) {
          e.preventDefault();
          var chosen = btn.getAttribute('data-lang-select');
          if (!SUPPORTED[chosen]) return;
          setLang(chosen);
          applyDir(chosen);
          // reload dictionary and re-apply
          loadJSON((window.STATIC_URL || '/static/') + 'core/i18n/' + chosen + '.json')
            .then(function (d) { applyTranslations(d); });
        });
      });
  }

  function boot() {
    var lang = getLang();
    if (!SUPPORTED[lang]) { lang = DEFAULT_LANG; setLang(lang); }
    applyDir(lang);
    loadJSON((window.STATIC_URL || '/static/') + 'core/i18n/' + lang + '.json')
      .then(function (dict) {
        applyTranslations(dict);
        initSwitcher(lang, dict);
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();


