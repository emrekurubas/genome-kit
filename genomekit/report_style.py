# Shared CSS + tooltip script for all generated pages (light and dark mode).
css = '''
:root{--bg:#fbfaf7;--fg:#1d1d1f;--mut:#5f6368;--card:#fff;--line:#e4e1da;--acc:#2f5d8a;--track:#efece6;
--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4;--s6:#008300;--s7:#4a3aa7;--s8:#e34948;--ok:#2e6b3a;--okbg:#e5f1e7;--mid:#8a5a00;--midbg:#fbefd6;--bad:#9b2c2c;--badbg:#f7e1e1;--old:#9b9a95}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#15171a;--fg:#e8e6e3;--mut:#a3a7ad;--card:#1d2024;--line:#30343a;--acc:#8fb6e0;--track:#2a2e33;
--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#008300;--s7:#9085e9;--s8:#e66767;--ok:#7fc38c;--okbg:#1f3324;--mid:#f0c060;--midbg:#3a2f15;--bad:#f09a9a;--badbg:#3b1f1f;--old:#7d7c78}}
:root[data-theme="dark"]{--bg:#15171a;--fg:#e8e6e3;--mut:#a3a7ad;--card:#1d2024;--line:#30343a;--acc:#8fb6e0;--track:#2a2e33;
--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#008300;--s7:#9085e9;--s8:#e66767;--ok:#7fc38c;--okbg:#1f3324;--mid:#f0c060;--midbg:#3a2f15;--bad:#f09a9a;--badbg:#3b1f1f;--old:#7d7c78}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif}
main{max-width:980px;margin:0 auto;padding:40px 16px 96px}
h1{font-size:34px;line-height:1.15;margin:0 0 8px;letter-spacing:-.01em}h2{font-size:24px;margin:56px 0 6px;letter-spacing:-.01em}h3{font-size:17px;margin:28px 0 8px}
.lede{font-size:18px;color:var(--mut);max-width:720px;margin:0}.mut{color:var(--mut)}.small{font-size:13.5px}.kicker{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--acc);font-weight:700;margin-bottom:10px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:28px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.card b{display:block;font-size:12px;letter-spacing:.05em;text-transform:uppercase;color:var(--mut);font-weight:600}
.card .big{font-size:30px;font-weight:700;line-height:1.2;margin:4px 0 2px;font-variant-numeric:tabular-nums}.card small{color:var(--mut);font-size:13px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px 20px 16px;margin:18px 0}
.legend{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:13.5px;color:var(--mut);margin:0 0 14px}.legend i{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.barrow{display:grid;grid-template-columns:170px 1fr 92px;gap:14px;align-items:center;margin:12px 0}
.barlab{font-size:14px;font-weight:600}.barlab small{display:block;font-weight:400;color:var(--mut);font-size:12.5px}
.bar{display:flex;gap:2px;height:34px}.seg{border-radius:4px;display:flex;align-items:center;justify-content:center;min-width:3px;cursor:default;outline-offset:2px}
.seg span{color:#fff;font-size:13px;font-weight:700;font-variant-numeric:tabular-nums;text-shadow:0 1px 1px rgba(0,0,0,.25)}
.pv{font-size:13px;font-weight:700;border-radius:8px;padding:4px 8px;text-align:center;font-variant-numeric:tabular-nums}.pv small{display:block;font-weight:500;font-size:11.5px}
.pv.ok{color:var(--ok);background:var(--okbg)}.pv.mid{color:var(--mid);background:var(--midbg)}.pv.bad{color:var(--bad);background:var(--badbg)}
.callout{border-left:3px solid var(--acc);background:var(--card);padding:12px 16px;border-radius:0 10px 10px 0;margin:16px 0;font-size:15px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.mrow{display:grid;grid-template-columns:130px 1fr 52px;gap:10px;align-items:center;font-size:14px;padding:3px 0}
.mtrack{height:10px;background:var(--track);border-radius:4px;overflow:hidden}.mbar{display:block;height:100%;background:var(--old);border-radius:4px}.mbar.acc{background:var(--s1)}
.mp{font-variant-numeric:tabular-nums;color:var(--mut);font-size:13px;text-align:right}
ol.near{padding-left:20px;margin:0}ol.near li{padding:2px 0}ol.near li span:first-child{margin-right:8px}
img.plot{width:100%;border-radius:10px;border:1px solid var(--line);background:#fff}
.tw{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut);font-weight:600}.num{text-align:right;font-variant-numeric:tabular-nums}
tr.flag td{color:var(--mut)}
.drow{display:grid;grid-template-columns:240px 1fr 40px;gap:12px;align-items:center}
.drow{padding:5px 0;font-size:14px;border-bottom:1px dashed var(--line)}.drow.flag{opacity:.55}
.dname{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.dval{text-align:right;font-weight:700;font-variant-numeric:tabular-nums}
.dtrack{position:relative;height:16px;background:linear-gradient(to right,transparent calc(25% - .5px),var(--line) calc(25% - .5px),var(--line) calc(25% + .5px),transparent calc(25% + .5px),transparent calc(50% - .5px),var(--line) calc(50% - .5px),var(--line) calc(50% + .5px),transparent calc(50% + .5px),transparent calc(75% - .5px),var(--line) calc(75% - .5px),var(--line) calc(75% + .5px),transparent calc(75% + .5px))}
.dline{position:absolute;top:7px;height:2px;background:var(--old);opacity:.6}
.dot{position:absolute;top:3px;width:10px;height:10px;margin-left:-5px;border-radius:50%;border:2px solid var(--card)}.dot.old{background:var(--old)}.dot.new{background:var(--s1)}
.dot.static{position:static;display:inline-block;margin:0 6px -1px 0;width:11px;height:11px}
.scale{display:grid;grid-template-columns:240px 1fr 40px;gap:12px;font-size:12px;color:var(--mut)}.scale div{display:flex;justify-content:space-between}
details{margin-top:14px}summary{cursor:pointer;color:var(--acc);font-weight:600;font-size:14px}
code{font-size:13px;background:var(--track);padding:1px 5px;border-radius:4px}
#tip{position:fixed;pointer-events:none;background:var(--fg);color:var(--bg);font-size:13px;padding:6px 10px;border-radius:8px;max-width:320px;opacity:0;transition:opacity .1s;z-index:9}

.crumbs{line-height:2.1}.crumb{background:var(--track);border-radius:6px;padding:2px 8px;font-weight:600;font-size:14px;white-space:nowrap}

a{color:var(--acc)}a:visited{color:var(--acc)}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]) img.plot{filter:brightness(.82) contrast(1.05)}}
:root[data-theme="dark"] img.plot{filter:brightness(.82) contrast(1.05)}
footer{margin-top:64px;font-size:13px;color:var(--mut);border-top:1px solid var(--line);padding-top:16px}
@media (max-width:700px){.seg span{font-size:11px}.seg.sm span{display:none}.barrow{grid-template-columns:1fr 84px}.barlab{grid-column:1/-1}.two{grid-template-columns:1fr}.drow,.scale{grid-template-columns:130px 1fr 34px}.dname{white-space:normal;line-height:1.25}h1{font-size:28px}}
'''
TIP_JS = '''<div id="tip" role="tooltip"></div>
<script>
const t=document.getElementById('tip');
function show(e,el){t.textContent=el.dataset.tip;t.style.opacity=1;const r=el.getBoundingClientRect();const x=e&&e.clientX!==undefined?e.clientX:r.left+r.width/2;const y=e&&e.clientY!==undefined?e.clientY:r.top;t.style.left=Math.min(x+12,innerWidth-t.offsetWidth-8)+'px';t.style.top=(y-t.offsetHeight-12<4?y+16:y-t.offsetHeight-12)+'px'}
document.querySelectorAll('[data-tip]').forEach(el=>{el.addEventListener('mousemove',e=>show(e,el));el.addEventListener('focus',()=>show(null,el));['mouseleave','blur'].forEach(ev=>el.addEventListener(ev,()=>t.style.opacity=0))});
</script>'''
