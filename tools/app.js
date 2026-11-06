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
