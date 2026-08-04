"""Generate the self-contained policy dashboard HTML (body content only, for the
Artifact wrapper): clickable Ghana map selector, coverage/cost/WTP sliders,
scenario table, and a live cost-effectiveness plane."""
import json

data = json.load(open("data/policy_dashboard_data.json"))
mp = json.load(open("data/ghana_paths.json"))
DATA = json.dumps(data, separators=(",", ":"))
MAP = json.dumps(mp, separators=(",", ":"))

HTML = r"""<style>
:root{
  --ground:#f5f3ee;--paper:#fffdf9;--ink:#1b1d19;--ink-soft:#4a4d45;--line:#e4e0d6;
  --teal:#0f6d62;--teal-deep:#0a4f47;--ochre:#b5761f;
  --good:#2e7d51;--good-bg:#e7f1ea;--warn:#a9761f;--warn-bg:#f6eedd;--bad:#9c463d;--bad-bg:#f3e4e1;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
}
*{box-sizing:border-box}
.wrap{max-width:1120px;margin:0 auto;padding:32px 22px 60px;color:var(--ink);
  font-family:var(--sans);background:var(--ground);line-height:1.5}
.eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--teal);margin:0 0 8px}
h1{font-family:var(--serif);font-weight:600;font-size:30px;line-height:1.12;margin:0 0 6px;
  text-wrap:balance;letter-spacing:-.01em}
.sub{color:var(--ink-soft);font-size:15px;margin:0 0 24px;max-width:70ch}

.top{display:grid;grid-template-columns:300px 1fr;gap:28px;margin-bottom:28px;align-items:start}
.mapcard{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:16px}
.mapcard h2{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-soft);
  margin:0 0 10px;font-weight:600}
svg.map{width:100%;height:auto;display:block}
svg.map .ctx{fill:#e9e5dc;stroke:#dcd7cb;stroke-width:.6}
svg.map .region{fill:#cfe0da;stroke:#fff;stroke-width:1.1;cursor:pointer;transition:fill .15s}
svg.map .region:hover{fill:#9dc4ba}
svg.map .region[aria-pressed=true]{fill:var(--teal)}
svg.map text{font-family:var(--sans);font-size:9px;fill:#33352f;pointer-events:none;text-anchor:middle;font-weight:600}
svg.map text.on{fill:#fff}
.maphint{font-size:11.5px;color:var(--ink-soft);margin:10px 0 0;font-family:var(--mono)}

.kpis{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}
.kpi{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:15px 16px 13px}
.kpi .lab{font-size:11px;letter-spacing:.04em;text-transform:uppercase;color:var(--ink-soft);margin:0 0 5px}
.kpi .val{font-family:var(--serif);font-size:25px;font-weight:600;letter-spacing:-.01em;
  font-variant-numeric:tabular-nums}
.kpi .val small{font-size:13px;font-weight:400;color:var(--ink-soft);font-family:var(--sans)}
.kpi .note{font-size:11.5px;color:var(--ink-soft);margin-top:4px}

.banner{background:var(--teal-deep);color:#f4efe4;border-radius:14px;padding:16px 20px;margin:0 0 8px;
  display:flex;gap:14px;align-items:flex-start;grid-column:1 / -1}
.banner .mark{font-size:20px}
.banner b{color:#fff}
.banner p{margin:0;font-size:14px;max-width:88ch}

.section-h{font-family:var(--serif);font-size:19px;font-weight:600;margin:30px 0 4px}
.section-d{font-size:13.5px;color:var(--ink-soft);margin:0 0 14px}

.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--paper)}
table{border-collapse:collapse;width:100%;font-size:13.5px;min-width:720px}
th,td{padding:11px 13px;text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
th:first-child,td:first-child{text-align:left}
thead th{font-size:11px;letter-spacing:.04em;text-transform:uppercase;color:var(--ink-soft);
  font-weight:600;border-bottom:1px solid var(--line);background:#faf8f2}
tbody tr{border-bottom:1px solid var(--line)}
tbody tr:last-child{border-bottom:0}
tbody tr.rec{background:#f0f6f3}
td.scen{font-weight:600}
.pill{display:inline-block;font-size:11px;font-weight:600;padding:3px 9px;border-radius:20px}
.pill.good{background:var(--good-bg);color:var(--good)}
.pill.warn{background:var(--warn-bg);color:var(--warn)}
.pill.bad{background:var(--bad-bg);color:var(--bad)}
.ce-yes{color:var(--good);font-weight:600}
.ce-no{color:var(--bad);font-weight:600}

.explorer{display:grid;grid-template-columns:320px 1fr;gap:26px;margin-top:16px;
  background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:22px}
.ctrl{margin-bottom:20px}
.ctrl label{display:flex;justify-content:space-between;font-size:13px;font-weight:600;margin-bottom:8px}
.ctrl label span{font-family:var(--mono);color:var(--teal);font-weight:500}
input[type=range]{width:100%;accent-color:var(--teal)}
.ctrl .rng{display:flex;justify-content:space-between;font-size:11px;color:var(--ink-soft);
  font-family:var(--mono);margin-top:3px}
.hint{font-size:12px;color:var(--ink-soft);margin-top:12px;line-height:1.45}
canvas{width:100%;height:auto;display:block}
.legend{display:flex;flex-wrap:wrap;gap:10px 16px;margin-top:10px;font-size:12px;color:var(--ink-soft)}
.legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:middle}
footer{margin-top:38px;padding-top:18px;border-top:1px solid var(--line);
  font-size:12px;color:var(--ink-soft);line-height:1.55}
@media(max-width:860px){.top{grid-template-columns:1fr}.explorer{grid-template-columns:1fr}
  svg.map{max-width:280px;margin:0 auto}}
</style>

<div class="wrap">
  <p class="eyebrow">EMOD transmission model · northern Ghana · 2023–2027 projection</p>
  <h1>Scaling up seasonal malaria chemoprevention: a policy decision dashboard</h1>
  <p class="sub">Modelled impact, burden averted and value-for-money of adding a fifth SMC cycle
    and extending eligibility beyond under-5s. Select a region on the map, then explore how the
    numbers shift with coverage, delivery cost and willingness to pay.</p>

  <div class="top">
    <div class="mapcard">
      <h2>Select region</h2>
      <div id="mapbox"></div>
      <p class="maphint" id="popLine"></p>
    </div>
    <div>
      <div class="kpis" id="kpis"></div>
    </div>
    <div class="banner">
      <span class="mark">▲</span>
      <p><b>Add the fifth cycle before extending age.</b> Across all three regions the efficient path
        is SMC-5 (U5) → SMC-5 (U10) → SMC-5 (U15). Age extension <i>without</i> a fifth cycle
        (SMC-4 U10/U15) is dominated. <span id="bannerCE"></span></p>
    </div>
  </div>

  <div class="section-h">Scenario comparison <span id="regName"></span></div>
  <div class="section-d">Impact = mean reduction in clinical malaria incidence vs the current
    4-cycle under-5 programme. Burden averted and cost are region-wide, per year, at the coverage set below.</div>
  <div class="tablewrap"><table id="tbl">
    <thead><tr>
      <th>Scenario</th><th>Under-5<br>impact</th><th>5–10y<br>impact</th>
      <th>Deaths<br>averted/yr</th><th>Cases<br>averted/yr</th><th>Cost/yr</th>
      <th>$/DALY</th><th>Cost-<br>effective?</th><th>Value</th>
    </tr></thead><tbody></tbody>
  </table></div>

  <div class="section-h">Explore the assumptions</div>
  <div class="section-d">Coverage scales the reach (burden averted and total cost); cost per course and
    willingness to pay set the economics. Cost-effective points sit below the threshold line.</div>
  <div class="explorer">
    <div>
      <div class="ctrl">
        <label>SMC coverage <span id="covVal">85%</span></label>
        <input type="range" id="cov" min="40" max="95" step="1" value="85">
        <div class="rng"><span>40%</span><span>95%</span></div>
      </div>
      <div class="ctrl">
        <label>Cost per child-course <span id="cpcVal">$0.90</span></label>
        <input type="range" id="cpc" min="0.30" max="2.50" step="0.05" value="0.90">
        <div class="rng"><span>$0.30</span><span>$2.50</span></div>
      </div>
      <div class="ctrl">
        <label>Willingness to pay <span id="wtpVal">$1,200 / DALY</span></label>
        <input type="range" id="wtp" min="100" max="2400" step="50" value="1200">
        <div class="rng"><span>$100</span><span>$2,400 (GDP)</span></div>
      </div>
      <p class="hint">Coverage scales impact and cost proportionally (first-order; indirect
        transmission effects not re-simulated). Thresholds: 0.5× and 1× Ghana GDP per capita
        (~$1,200 / $2,400 per DALY). DALY parameters held at base case.</p>
    </div>
    <div>
      <canvas id="plane" width="720" height="420"></canvas>
      <div class="legend" id="legend"></div>
    </div>
  </div>

  <footer id="foot"></footer>
</div>

<script>
window.addEventListener("error", e => {
  const f = document.getElementById("foot");
  if (f) f.textContent = "⚠ Script error: " + e.message + "  (line " + e.lineno + ")";
});
const D = __DATA__;
const MAP = __MAP__;
const SCEN = ["5cycle","5cycle_age10","5cycle_age15","age10","age15"];
const P = D.params, COVREF = 0.85;
const NAMES = {upper_east:"Upper East",upper_west:"Upper West",northern:"Northern"};
let region = "upper_east", cov = 0.85, cpc = 0.90, wtp = 1200;
const fmt = n => Math.round(n).toLocaleString();
const money = n => "$"+fmt(n);
const covMult = () => cov / COVREF;

function recompute(sc){
  const c = D.regions[region][sc].counts, m = covMult();
  const cost = c.courses*m*cpc;
  const sev = c.sev*m, clin = c.clin*m;
  const daly = sev*P.cfr*P.yll + clin*0.006 + sev*(1-P.cfr)*0.05;
  // health-system perspective: SMC cost minus the case-management cost it averts
  const net = cost - (clin*P.cost_out + sev*P.cost_sev);
  return {cost, daly, net, deaths:sev*P.cfr, clin, upd:cost/daly, ce:(cost/daly)<wtp};
}
// how many scenarios clear the current WTP / are cost-saving, at the current sliders
function ceCounts(){
  const all = SCEN.map(sc=>recompute(sc));
  return {n:SCEN.length, ce:all.filter(p=>p.ce).length, save:all.filter(p=>p.net<0).length};
}
const nWord = (k,n) => k===n ? "all "+n : k+" of "+n;
const badge = f => f==="frontier" ? '<span class="pill good">On frontier</span>'
  : f==="ext-dominated" ? '<span class="pill warn">Poor value</span>'
  : '<span class="pill bad">Dominated</span>';
const COL = {frontier:"#0f6d62","ext-dominated":"#b5761f",dominated:"#9c463d"};

function renderMap(){
  let s = `<svg class="map" id="map" viewBox="${MAP.viewBox}" role="group" aria-label="Region map">`;
  s += `<path class="ctx" d="${MAP.context}"/>`;
  for(const k of Object.keys(MAP.study))
    s += `<path class="region" data-r="${k}" tabindex="0" role="button" aria-pressed="${k===region}"
      aria-label="${NAMES[k]}" d="${MAP.study[k]}"></path>`;
  for(const k of Object.keys(MAP.labels)){
    const [x,y]=MAP.labels[k];
    s += `<text class="${k===region?'on':''}" x="${x}" y="${y}">${NAMES[k].split(' ')[1]||NAMES[k]}</text>`;
  }
  s += `</svg>`;
  document.getElementById("mapbox").innerHTML = s;   // set on HTML container, not on <svg>
  document.querySelectorAll("#map .region").forEach(el=>{
    const pick = ()=>{ region = el.dataset.r; renderAll(); };
    el.addEventListener("click", pick);
    el.addEventListener("keydown", e=>{ if(e.key==="Enter"||e.key===" "){e.preventDefault();pick();} });
  });
}
function renderKpis(){
  const full = recompute("5cycle_age15");
  // cheapest per DALY, rather than assuming it is always SMC-5 (U5)
  const best = SCEN.map(sc=>({sc,...recompute(sc)})).reduce((a,b)=>b.upd<a.upd?b:a);
  const cc = ceCounts();
  const k = [
    ["Deaths averted / yr", fmt(full.deaths), "full package (SMC-5, U15)"],
    ["Cases averted / yr", fmt(full.clin), "full package (SMC-5, U15)"],
    ["Best value", money(best.upd)+" <small>/DALY</small>", D.labels[best.sc]],
    ["Cost-effectiveness", cc.ce===cc.n ? "All "+cc.n : cc.ce+" of "+cc.n,
     "cost-effective at "+money(wtp)+"/DALY · "+nWord(cc.save,cc.n)+" cost-saving"]
  ];
  const cs = cc;
  document.getElementById("bannerCE").innerHTML = cs.ce===cs.n && cs.save===cs.n
    ? "At "+money(wtp)+"/DALY and $"+cpc.toFixed(2)+"/course, every scenario is cost-effective "+
      "and cost-saving to the health system."
    : "At "+money(wtp)+"/DALY and $"+cpc.toFixed(2)+"/course, "+nWord(cs.ce,cs.n)+
      " scenarios are cost-effective and "+nWord(cs.save,cs.n)+" are cost-saving to the health system.";
  document.getElementById("kpis").innerHTML = k.map(x=>
    `<div class="kpi"><p class="lab">${x[0]}</p><div class="val">${x[1]}</div><div class="note">${x[2]}</div></div>`).join("");
}
function renderTable(){
  const tb = document.querySelector("#tbl tbody"); tb.innerHTML="";
  for(const sc of SCEN){
    const r = D.regions[region][sc], m = recompute(sc);
    const imp = a => r.impact[a]==null ? "—" : r.impact[a].toFixed(1)+"%";
    tb.innerHTML += `<tr${r.frontier==="frontier"?' class="rec"':''}>
      <td class="scen">${D.labels[sc]}</td><td>${imp("U5")}</td><td>${imp("5-10")}</td>
      <td>${fmt(m.deaths)}</td><td>${fmt(m.clin)}</td><td>${money(m.cost)}</td>
      <td>${money(m.upd)}</td>
      <td class="${m.ce?'ce-yes':'ce-no'}">${m.ce?'Yes':'No'}</td>
      <td>${badge(r.frontier)}</td></tr>`;
  }
}
// gridline values at a "nice" step (1/2/2.5/5 x power of ten) spanning 0..max
function ticks(max,n){
  const mag=Math.pow(10,Math.floor(Math.log10(max/n)));
  const step=([1,2,2.5,5,10].find(s=>s*mag>=max/n)||10)*mag;
  const out=[]; for(let v=0; v<=max*1.0001; v+=step) out.push(v);
  return out;
}
function renderPlane(){
  const cv=document.getElementById("plane"), x=cv.getContext("2d");
  const W=cv.width,H=cv.height,pad=66,top=18,right=16; x.clearRect(0,0,W,H);
  const pts=SCEN.map(sc=>({sc,...recompute(sc)}));
  const maxD=Math.max(...pts.map(p=>p.daly))*1.18, maxC=Math.max(...pts.map(p=>p.cost))*1.25/1e6;
  const X=d=>pad+d/maxD*(W-pad-right), Y=c=>H-pad-c/maxC*(H-pad-top);
  const tx=ticks(maxD,5), ty=ticks(maxC,4);
  x.font="11px system-ui";
  x.strokeStyle="#ece8de"; x.lineWidth=1;
  for(const v of ty){                                    // cost gridlines + labels
    x.beginPath(); x.moveTo(pad,Y(v)); x.lineTo(W-right,Y(v)); x.stroke();
    x.fillStyle="#7b7e75"; x.textAlign="right"; x.textBaseline="middle";
    x.fillText(v<1?"$"+(v*1000).toFixed(0)+"k":"$"+v.toFixed(v<10?1:0)+"m", pad-8, Y(v));
  }
  for(const v of tx){                                    // DALY gridlines + labels
    x.strokeStyle="#f2efe7"; x.beginPath(); x.moveTo(X(v),top); x.lineTo(X(v),H-pad); x.stroke();
    x.fillStyle="#7b7e75"; x.textAlign="center"; x.textBaseline="top";
    x.fillText(v>=1000?(v/1000)+"k":fmt(v), X(v), H-pad+7);
  }
  x.textAlign="left"; x.textBaseline="alphabetic";
  x.save(); x.beginPath(); x.rect(pad,top,W-right-pad,H-pad-top); x.clip();
  x.strokeStyle="#c9603f"; x.setLineDash([6,4]); x.lineWidth=1.4; x.beginPath();
  x.moveTo(X(0),Y(0)); x.lineTo(X(maxD),Y(wtp*maxD/1e6)); x.stroke(); x.setLineDash([]); x.restore();
  const lx=Math.min(maxD,maxC*1e6/wtp);
  x.fillStyle="#c9603f";
  x.fillText(money(wtp)+"/DALY threshold", X(lx*0.6)+4, Y(wtp*lx*0.6/1e6)-6);
  x.fillStyle="#4a4d45"; x.font="12px system-ui";
  x.fillText("DALYs averted / yr →", pad, H-14);
  x.save(); x.translate(16,H-pad); x.rotate(-Math.PI/2); x.fillText("Cost / yr (US$m) →",0,0); x.restore();
  for(const p of pts){
    x.fillStyle=COL[D.regions[region][p.sc].frontier]; x.globalAlpha=p.ce?1:0.45;
    x.beginPath(); x.arc(X(p.daly),Y(p.cost/1e6),7,0,7); x.fill();
    x.globalAlpha=1; x.fillStyle="#1b1d19"; x.font="11px system-ui";
    x.fillText(D.labels[p.sc], X(p.daly)+11, Y(p.cost/1e6)+4);
  }
  document.getElementById("legend").innerHTML =
    '<span><i style="background:#0f6d62"></i>On frontier</span>'+
    '<span><i style="background:#b5761f"></i>Extended-dominated</span>'+
    '<span><i style="background:#9c463d"></i>Dominated</span>'+
    '<span>faded = above threshold</span>';
}
function renderAll(){
  document.querySelectorAll("#map .region").forEach(el=>el.setAttribute("aria-pressed", el.dataset.r===region));
  document.querySelectorAll("#map text").forEach(t=>t.setAttribute("class",""));
  const on=[...document.querySelectorAll("#map .region")].find(e=>e.dataset.r===region);
  document.getElementById("popLine").textContent =
    NAMES[region]+" · under-15 pop "+D.pop_u15[region].toLocaleString();
  document.getElementById("regName").textContent = "— "+NAMES[region];
  renderKpis(); renderTable(); renderPlane();
  // recolor active label
  const svg=document.getElementById("map");
  [...svg.querySelectorAll("text")].forEach(t=>{ if(t.textContent===(NAMES[region].split(' ')[1]||NAMES[region])) t.setAttribute("class","on"); });
}
document.getElementById("cov").oninput=e=>{cov=+e.target.value/100; document.getElementById("covVal").textContent=e.target.value+"%"; renderKpis();renderTable();renderPlane();};
document.getElementById("cpc").oninput=e=>{cpc=+e.target.value; document.getElementById("cpcVal").textContent="$"+cpc.toFixed(2); renderKpis();renderTable();renderPlane();};
document.getElementById("wtp").oninput=e=>{wtp=+e.target.value; document.getElementById("wtpVal").textContent="$"+wtp.toLocaleString()+" / DALY"; renderKpis();renderTable();renderPlane();};
document.getElementById("foot").innerHTML =
  "Stochastic agent-based EMOD malaria model (2023–2027, mean of 60 realisations), calibrated to regional "+
  "RDT prevalence; “Northern” = the pre-2019 undivided region. DALYs from severe-case fatality "+
  "(0.10) and GBD disability weights; provider-perspective costs at a base $0.90/child-course. "+
  "Coverage scaling is first-order (indirect transmission effects not re-simulated). Modelled "+
  "projections for policy exploration, not observed outcomes. Region boundaries: geoBoundaries (gbOpen).";

renderMap(); renderAll();
</script>"""

body = HTML.replace("__DATA__", DATA).replace("__MAP__", MAP)
page = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="description" content="Modelled impact and cost-effectiveness of '
        'expanding seasonal malaria chemoprevention in northern Ghana, 2023-2027.">'
        "<title>Ghana SMC Policy Dashboard</title></head><body>" + body + "</body></html>")
# dashboard.html   — body fragment, for the Artifact wrapper
# SMC_Dashboard.html — standalone copy to open locally / send to people
# index.html       — the same standalone page, served by GitHub Pages
# All three are (re)written on every run so no copy can go stale.
open("dashboard.html", "w").write(body)
open("SMC_Dashboard.html", "w").write(page)
open("index.html", "w").write(page)
print(f"wrote dashboard.html ({len(body)} bytes), SMC_Dashboard.html, index.html")
