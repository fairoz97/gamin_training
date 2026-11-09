"""Floating REFRESH button injected into the built dashboards (coach, tinkerer, brain).

- opened from disk (file://)       -> tells you to start serve.py
- served by serve.py (localhost)   -> re-runs pull.py + build_all.py, then reloads
- hosted somewhere (https://...)   -> just reloads (hosted data updates on its own schedule)
"""

WIDGET = r"""
<style>
#__rf{position:fixed;right:14px;bottom:14px;z-index:2147483000;display:flex;flex-direction:column;align-items:flex-end;gap:6px;
  font:600 11px/1.2 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;letter-spacing:.12em}
#__rf button{cursor:pointer;color:#22e5ff;background:rgba(8,12,20,.9);border:1px solid #22e5ff;padding:8px 13px;border-radius:999px;font:inherit}
#__rf button:hover:not(:disabled){box-shadow:0 0 12px rgba(34,229,255,.55)}
#__rf button:disabled{opacity:.65;cursor:progress}
#__rf button.err{color:#ff4d6d;border-color:#ff4d6d}
#__rf span{display:none;max-width:260px;color:#ffb020;background:rgba(8,12,20,.92);padding:5px 9px;border-radius:6px;letter-spacing:.04em;font-weight:500}
</style>
<div id="__rf"><span id="__rfs"></span><button id="__rfb" type="button">↻ REFRESH</button></div>
<script>
(function(){
  var btn=document.getElementById('__rfb'), st=document.getElementById('__rfs');
  var local=location.protocol==='file:', dev=/^(127\.0\.0\.1|localhost)$/.test(location.hostname);
  if(!local&&!dev){ btn.textContent='↻ RELOAD'; btn.title='Reload the latest published data'; }
  if(local){ btn.title='Run "python serve.py" to enable refresh'; }
  function say(t,title){ st.textContent=t; st.title=title||''; st.style.display=t?'block':'none'; }
  btn.addEventListener('click', async function(){
    if(local){ say('START: python serve.py'); return; }
    if(!dev){ location.reload(); return; }
    btn.disabled=true; btn.classList.remove('err'); btn.textContent='PULLING…'; say('0s');
    var t0=Date.now(), tick=setInterval(function(){ say(Math.round((Date.now()-t0)/1000)+'s'); },1000);
    try{
      var r=await fetch('/refresh',{method:'POST',headers:{'X-Commander':'1'}});
      var j=await r.json().catch(function(){return {ok:false,log:'HTTP '+r.status}});
      if(!j.ok) throw new Error(j.log||('HTTP '+r.status));
      clearInterval(tick); btn.textContent='✓ DONE'; location.reload();
    }catch(e){
      clearInterval(tick); btn.disabled=false; btn.classList.add('err'); btn.textContent='↻ RETRY';
      var m=String(e.message||e).trim().split('\n').filter(Boolean).slice(-1)[0]||'failed';
      say(m.slice(0,140), String(e.message||e));
    }
  });
})();
</script>
"""


def inject(html: str) -> str:
    head, sep, tail = html.rpartition("</body>")
    return head + WIDGET + sep + tail if sep else html + WIDGET
