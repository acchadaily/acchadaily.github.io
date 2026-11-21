(function(){
  // Old #/slug links -> real story pages
  var m = location.hash.match(/^#\/(.+)/);
  if (m && window.SLUGS && SLUGS[m[1]]) { location.replace(SLUGS[m[1]]); return; }

  // Reading progress bar
  var bar = document.getElementById('bar');
  if (bar) {
    var art = document.querySelector('article');
    var upd = function(){
      var r = art.getBoundingClientRect(), h = art.offsetHeight - innerHeight;
      bar.style.width = Math.max(0, Math.min(1, -r.top / (h > 0 ? h : 1))) * 100 + '%';
    };
    addEventListener('scroll', upd, {passive:true}); upd();
  }

  // Share / copy link
  document.querySelectorAll('[data-share]').forEach(function(b){
    b.addEventListener('click', function(){
      var d = {title: document.title, url: location.href.split('#')[0]};
      if (navigator.share) { navigator.share(d).catch(function(){}); return; }
      (navigator.clipboard ? navigator.clipboard.writeText(d.url) : Promise.reject()).then(function(){
        var t = b.innerHTML; b.textContent = 'Link copied ✓'; setTimeout(function(){ b.innerHTML = t; }, 1600);
      }).catch(function(){ prompt('Copy this link', d.url); });
    });
  });

  // Topic filter chips
  var chips = document.querySelectorAll('.chip');
  chips.forEach(function(c){
    c.addEventListener('click', function(){
      var t = c.dataset.t;
      chips.forEach(function(x){ x.setAttribute('aria-pressed', x === c); });
      document.querySelectorAll('[data-tag]').forEach(function(s){
        s.classList.toggle('hidden', t !== '*' && s.dataset.tag !== t);
      });
      document.querySelectorAll('[data-block]').forEach(function(b){
        b.classList.toggle('hidden', !b.querySelector('[data-tag]:not(.hidden)'));
      });
    });
  });

  // Search page
  var q = document.getElementById('q');
  if (q) {
    var res = document.getElementById('res'), idx = null;
    var esc = function(s){ return s.replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); };
    var run = function(){
      var words = q.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
      history.replaceState(null, '', words.length ? '?q=' + encodeURIComponent(q.value) : location.pathname);
      if (!words.length) { res.innerHTML = '<p class="empty">Type a brand, a person or a topic — e.g. Blinkit, Ronaldo, gold.</p>'; return; }
      var hits = idx.filter(function(s){ var t = s.x; return words.every(function(w){ return t.indexOf(w) > -1; }); }).slice(0, 40);
      res.innerHTML = hits.length ? hits.map(function(s){
        return '<a class="row st" href="' + s.u + '"><div><span class="tag" style="--c:' + s.c + '"><i></i>' + esc(s.g) + '</span> <span class="rt">' + esc(s.d) + '</span><h4>' + esc(s.h) + '</h4><p>' + esc(s.k) + '</p></div></a>';
      }).join('') : '<p class="empty">No stories found for “' + esc(q.value) + '”.</p>';
    };
    fetch('/search.json').then(function(r){ return r.json(); }).then(function(j){
      idx = j.map(function(s){ s.x = (s.h + ' ' + s.k + ' ' + s.g + ' ' + s.d).toLowerCase(); return s; });
      var p = new URLSearchParams(location.search).get('q'); if (p) q.value = p;
      run(); q.addEventListener('input', run);
    });
  }
})();

// 60-second swipe mode
(function(){
  var w = document.getElementById('bf'); if (!w) return;
  var cards = w.querySelectorAll('.bf'), n = cards.length - 1, p = document.getElementById('bfp'), c = document.getElementById('bfn'), h = document.getElementById('bfh');
  var cur = 0;
  var upd = function(){
    cur = Math.round(w.scrollTop / w.clientHeight);
    var k = Math.min(cur + 1, n);
    p.style.width = (k / n * 100) + '%'; c.textContent = (cur >= n ? n : k) + '/' + n;
    if (cur > 0) h.classList.add('gone');
  };
  w.addEventListener('scroll', upd, {passive:true}); upd();
  var go = function(i){ i = Math.max(0, Math.min(cards.length - 1, i)); w.scrollTo({top: i * w.clientHeight, behavior: 'smooth'}); };
  addEventListener('keydown', function(ev){
    if (ev.key === 'ArrowDown' || ev.key === 'ArrowRight' || ev.key === ' ' || ev.key === 'PageDown') { ev.preventDefault(); go(cur + 1); }
    if (ev.key === 'ArrowUp' || ev.key === 'ArrowLeft' || ev.key === 'PageUp') { ev.preventDefault(); go(cur - 1); }
    if (ev.key === 'Escape') location.href = w.querySelector('.bf-top a').href;
  });
  w.focus();
})();

/* Newsletter signup — submit in place.
   Kit's plain form POST navigates the reader off to app.kit.com, which is a
   bad way to end a visit. This posts the same body with fetch and swaps in
   our own message. Kit allows the cross-origin POST (access-control-allow-
   origin: *) and returns JSON on 200. Without JS the form still works as an
   ordinary POST, so this is pure progressive enhancement. */
(function () {
  var f = document.querySelector('.sub-f');
  if (!f || !window.fetch) return;
  var box = f.closest('.sub-box');
  var input = f.querySelector('input[name="email_address"]');
  var btn = f.querySelector('button');

  function note(text, bad) {
    var n = box.querySelector('.sub-note') || document.createElement('p');
    n.className = 'sub-note' + (bad ? ' bad' : '');
    n.textContent = text;
    /* append to the box, not relative to the form: on success the form is
       already detached, and inserting next to a detached node is a no-op. */
    if (!n.parentNode) box.insertBefore(n, box.querySelector('small'));
  }

  f.addEventListener('submit', function (ev) {
    ev.preventDefault();
    if (!input.value || !f.checkValidity()) return;
    btn.disabled = true;
    var label = btn.textContent;
    btn.textContent = 'Sending…';

    fetch(f.action, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
      },
      body: 'email_address=' + encodeURIComponent(input.value)
    }).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      var confirm = f.getAttribute('data-confirm') === '1';
      var sender = f.getAttribute('data-sender') || '';
      f.remove();
      note(confirm
        ? 'Almost there — check your inbox and click the confirmation link.'
        : "You're in. The next edition lands in your inbox tomorrow morning.");
      /* A sending domain this new gets filtered for weeks. Allow-listing is the
         one thing the reader can actually do about it, and this is the only
         moment we have to ask: with single opt-in there is no welcome email. */
      if (sender) {
        var tip = document.createElement('div');
        tip.className = 'sub-tip';
        tip.innerHTML =
          '<b>One quick thing</b> — add <code>' + sender + '</code> to your contacts, ' +
          'or the first few may land in spam.' +
          '<span>Gmail: open the email \u2192 tap the \u22ee \u2192 <em>Add to contacts</em>. ' +
          'If it went to Spam, tap <em>Report not spam</em> first.</span>';
        box.insertBefore(tip, box.querySelector('small'));
      }
    }).catch(function () {
      btn.disabled = false;
      btn.textContent = label;
      note('That didn’t go through. Please try again in a moment.', true);
    });
  });
})();
