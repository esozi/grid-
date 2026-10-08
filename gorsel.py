# -*- coding: utf-8 -*-
"""Tıklanabilir, animasyonlu şebeke şeması (pandapower sonuçlarından)."""
import json
import math

TEMPLATE = r"""
<style>
:root{--bg:#fff;--fg:#14212B;--fg2:#52626F;--ok:#2E8B57;--wr:#D98E04;--bd:#D1432E;--card:#F3F5F7;--bl:#1D5FD1}
@media (prefers-color-scheme:dark){:root{--bg:#0E1117;--fg:#E6EDF3;--fg2:#9FB0BE;--ok:#3FB27A;--wr:#E8A91F;--bd:#F26B55;--card:#1B222C;--bl:#6AA3FF}}
body{margin:0;background:var(--bg);color:var(--fg);font-family:'IBM Plex Sans',Arial,sans-serif;font-size:14px}
#w{display:flex;gap:12px;flex-wrap:wrap;padding:8px;box-sizing:border-box}
#m{flex:1 1 560px;min-width:0}#p{flex:0 0 280px;background:var(--card);border-radius:8px;padding:12px;box-sizing:border-box}
#bar{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:6px;font-size:12px;color:var(--fg2)}
#t{height:32px;padding:0 12px;border:1px solid var(--fg2);background:transparent;color:var(--fg);border-radius:6px;cursor:pointer}
.lg i{display:inline-block;width:14px;height:8px;border-radius:2px;margin:0 4px 0 10px}
svg{width:100%;height:auto;max-height:560px}
.ln{fill:none;stroke-width:8;stroke-linecap:round}.cn{fill:none;stroke:var(--fg2);stroke-width:4}
.flow{fill:none;stroke:#fff;stroke-width:3;stroke-dasharray:8 14;stroke-linecap:round;animation:mv linear infinite}
.flow.rev{animation-direction:reverse}@keyframes mv{to{stroke-dashoffset:-44}}
.paused .flow{animation-play-state:paused}
@media (prefers-reduced-motion:reduce){.flow{animation:none}}
.hh{fill:none;stroke:transparent;stroke-width:26}.hh2{fill:transparent}.hit{cursor:pointer}
.sel{filter:drop-shadow(0 0 5px var(--bl))}
.tx{font-size:13px;font-weight:600;fill:var(--fg)}.tx2{font-size:12px;fill:var(--fg2)}.sym{font-size:22px;fill:var(--fg)}
.tr,.src{fill:var(--bg);stroke:var(--fg);stroke-width:2.5}.ar{fill:var(--fg)}
h3{margin:0 0 8px;font-size:15px}table{width:100%;border-collapse:collapse;font-size:13px}td{padding:4px 0;border-top:1px solid rgba(128,128,128,.25)}
td:last-child{text-align:right}p{font-size:13px;line-height:1.45;margin:10px 0 0}
</style>
<div id="w"><div id="m"><div id="bar"><button id="t">Animasyon: Açık</button>
<span class="lg">Yüklenme:<i style="background:var(--ok)"></i>%60 altı<i style="background:var(--wr)"></i>%60-90<i style="background:var(--bd)"></i>%90 üstü</span>
<span>Hareketli çizgiler güç yönünü, hız büyüklüğü gösterir. Bir elemana tıklayın.</span></div>
<svg id="s" viewBox="0 0 1000 540" role="img" aria-label="Şebeke şeması"></svg></div><div id="p"></div></div>
<script>
const D=__DATA__,NS='http://www.w3.org/2000/svg',S=document.getElementById('s'),P=document.getElementById('p');
const E=(t,a,tx)=>{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);if(tx!=null)e.textContent=tx;S.appendChild(e);return e};
const col=l=>l>90?'var(--bd)':l>60?'var(--wr)':'var(--ok)';
const pm=Math.max(1,...D.br.map(b=>Math.abs(b.p)),...D.src.map(s=>Math.abs(s.p)));
const reg={};
function pick(id){document.querySelectorAll('.sel').forEach(e=>e.classList.remove('sel'));reg[id].hi.forEach(e=>e.classList.add('sel'));P.innerHTML=reg[id].html()}
function bind(id,click,hi,html){reg[id]={hi:hi,html:html};click.forEach(e=>{e.classList.add('hit');e.addEventListener('click',()=>pick(id))})}
function flow(d,p){if(Math.abs(p)<0.05)return;const f=E('path',{d:d,class:'flow'+(p<0?' rev':'')});f.style.animationDuration=(2.8-2.2*Math.min(1,Math.abs(p)/pm)).toFixed(2)+'s';f.style.pointerEvents='none'}
const f1=x=>Number(x).toFixed(1),f3=x=>Number(x).toFixed(3);
const R=(k,v)=>'<tr><td>'+k+'</td><td><b>'+v+'</b></td></tr>';
const box=(t,rows,note)=>'<h3>'+t+'</h3><table>'+rows.join('')+'</table><p>'+note+'</p>';
const around=n=>D.br.filter(b=>b.f===n||b.t===n).map(b=>{const o=b.f===n?b.t:b.f,out=b.f===n?b.p:b.pt;return '<tr><td colspan=2>'+b.n+' ('+o+'): '+(out>=0?'çıkış ':'giriş ')+f1(Math.abs(out))+' MW</td></tr>'});
D.br.forEach(b=>{
 const a=D.pos[b.f],c=D.pos[b.t],ring=b.ring;
 const d=ring?'M'+a[0]+' '+a[1]+' Q'+(a[0]+c[0])/2+' '+(a[1]+190)+' '+c[0]+' '+c[1]:'M'+a[0]+' '+a[1]+' L'+c[0]+' '+c[1];
 const ln=E('path',{d:d,class:'ln',stroke:col(b.load)});flow(d,b.p);
 const mx=(a[0]+c[0])/2,my=ring?a[1]+95:a[1],hi=[ln];
 if(b.k==='trafo'){hi.push(E('circle',{cx:mx-9,cy:my,r:15,class:'tr'}),E('circle',{cx:mx+9,cy:my,r:15,class:'tr'}))}
 const ty=ring?my+26:my-30;
 E('text',{x:mx,y:ty,'text-anchor':'middle',class:'tx2'},b.n);E('text',{x:mx,y:ty+14,'text-anchor':'middle',class:'tx'},f1(Math.abs(b.p))+' MW');
 const h=E('path',{d:d,class:'hh'});
 bind(b.id,[h].concat(hi.slice(1)),hi,()=>box((b.k==='trafo'?'Trafo ':'Hat ')+b.n,[R('Güç yönü',b.p>=0?b.f+' → '+b.t:b.t+' → '+b.f),R('Aktif güç',f1(Math.abs(b.p))+' MW'),R('Reaktif güç',f1(b.q)+' MVAr'),R('Yüklenme','%'+f1(b.load)),R('Kayıp',f3(b.pl)+' MW')],b.load>100?'Aşırı yüklü: kesiti büyütün veya paralel hat/trafo ekleyin.':b.load>60?'Yüklenme yüksek, izleyin.':'Yüklenme uygun.'));
});
D.bus.forEach(u=>{const [x,y]=D.pos[u.id],bad=u.v<0.95||u.v>1.05;
 const r=E('rect',{x:x-5,y:y-34,width:10,height:68,rx:3,fill:bad?'var(--bd)':'var(--fg)'});
 E('text',{x:x,y:y-42,'text-anchor':'middle',class:'tx'},u.n);
 E('text',{x:x+10,y:y+52,'text-anchor':'start',class:'tx2',fill:bad?'var(--bd)':'var(--fg2)'},f3(u.v)+' pu');
 const h=E('rect',{x:x-14,y:y-40,width:28,height:80,class:'hh2'});
 bind(u.id,[h],[r],()=>box('Bara '+u.n,[R('Nominal gerilim',u.vn+' kV'),R('Gerilim',f3(u.v)+' pu ('+f1(u.v*u.vn)+' kV)'),R('Açı',f1(u.a)+'°')].concat(around(u.id)),bad?'Gerilim limit dışı (0.95-1.05 pu). Kesit büyütmeyi, halka kapatmayı veya generatör gerilim ayarını artırmayı deneyin.':'Gerilim limit içinde.'));
});
D.src.forEach(s=>{const [x,y]=D.pos[s.id],b=D.pos[s.bus],e=s.k==='ext';
 const d=e?'M'+(x+22)+' '+y+' L'+(b[0]-5)+' '+b[1]:'M'+x+' '+(y+22)+' L'+b[0]+' '+(b[1]-34);
 E('path',{d:d,class:'cn'});flow(d,s.p);
 const c=E('circle',{cx:x,cy:y,r:22,class:'src'});E('text',{x:x,y:y+7,'text-anchor':'middle',class:'sym','pointer-events':'none'},e?'~':'G');
 const ly=e?y+42:y-30;E('text',{x:x,y:ly,'text-anchor':'middle',class:'tx2'},s.n);E('text',{x:x,y:ly+14,'text-anchor':'middle',class:'tx'},(s.p>=0?'+':'')+f1(s.p)+' MW');
 bind(s.id,[c],[c],()=>box((e?'Dış şebeke ':'Generatör ')+s.n,[R('Aktif güç',f1(s.p)+' MW'),R('Reaktif güç',f1(s.q)+' MVAr'),R('Bara',s.bus_n+' ('+f3(s.v)+' pu)')].concat(around(s.bus)),e?(s.p>=0?'Yük ve kayıpları karşılamak için şebekeye güç veriyor.':'Fazla üretim ('+f1(-s.p)+' MW) enterkonnekte sisteme akıyor.'):'Şebekeye '+f1(s.p)+' MW veriyor. Çıkış yolları yukarıda: hangi hatlardan gittiğini görün.'));
});
D.ld.forEach(l=>{const [x,y]=D.pos[l.id],b=D.pos[l.bus];const d='M'+b[0]+' '+(b[1]+34)+' L'+x+' '+(y-16);
 E('path',{d:d,class:'cn'});flow(d,l.p);
 const a=E('polygon',{points:(x-9)+','+(y-16)+' '+(x+9)+','+(y-16)+' '+x+','+(y+2),class:'ar'});
 E('text',{x:x,y:y+22,'text-anchor':'middle',class:'tx2'},l.n);E('text',{x:x,y:y+36,'text-anchor':'middle',class:'tx'},f1(l.p)+' MW / '+f1(l.q)+' MVAr');
 const h=E('rect',{x:x-24,y:b[1]+34,width:48,height:y-b[1]-30,class:'hh2'});
 bind(l.id,[h],[a],()=>box('Yük '+l.n,[R('Aktif güç',f1(l.p)+' MW'),R('Reaktif güç',f1(l.q)+' MVAr'),R('Bara',l.bus_n)],'Bu yük beslenmeli; gerilim ve hat yüklenmesi buna göre oluşur.'));
});
const T=document.getElementById('t');T.onclick=()=>{const p=S.classList.toggle('paused');T.textContent='Animasyon: '+(p?'Kapalı':'Açık')};
pick((D.src.find(s=>s.k==='gen')||D.src[0]).id);
</script>
"""


def _n(x, d=4):
    x = float(x)
    return 0.0 if math.isnan(x) else round(x, d)


def veri(net):
    hv = [b for b in net.bus.index if net.bus.at[b, "vn_kv"] >= 100]
    n = len(hv)
    step = min(150, 640 / max(1, n - 1))
    pos = {}
    bus = []
    for k, b in enumerate(hv):
        pos[f"b{b}"] = [130 + k * step, 190]
    lv = [b for b in net.bus.index if b not in hv]
    last_x = 130 + (n - 1) * step
    for j, b in enumerate(lv):
        pos[f"b{b}"] = [last_x + 170, 190]
    if "gx" in net.bus.columns:
        for b in net.bus.index:
            pos[f"b{b}"] = [float(net.bus.at[b, "gx"]), float(net.bus.at[b, "gy"])]
    rb = net.res_bus
    for b in net.bus.index:
        bus.append({"id": f"b{b}", "n": net.bus.at[b, "name"], "vn": float(net.bus.at[b, "vn_kv"]),
                    "v": _n(rb.at[b, "vm_pu"]), "a": _n(rb.at[b, "va_degree"], 2)})
    nm = lambda b: f"b{b}"
    br = []
    for l in net.line.index:
        f, t = int(net.line.at[l, "from_bus"]), int(net.line.at[l, "to_bus"])
        r = net.res_line.loc[l]
        br.append({"id": f"l{l}", "k": "line", "n": net.line.at[l, "name"], "f": nm(f), "t": nm(t),
                   "p": _n(r.p_from_mw), "pt": _n(r.p_to_mw), "q": _n(r.q_from_mvar),
                   "load": _n(r.loading_percent, 1), "pl": _n(r.pl_mw),
                   "ring": net.line.at[l, "name"] == "L_halka"})
    for t in net.trafo.index:
        r = net.res_trafo.loc[t]
        br.append({"id": f"t{t}", "k": "trafo", "n": net.trafo.at[t, "name"],
                   "f": nm(int(net.trafo.at[t, "hv_bus"])), "t": nm(int(net.trafo.at[t, "lv_bus"])),
                   "p": _n(r.p_hv_mw), "pt": _n(r.p_lv_mw), "q": _n(r.q_hv_mvar),
                   "load": _n(r.loading_percent, 1), "pl": _n(r.pl_mw), "ring": False})
    # etiketlerde bara adı kullan
    name_of = {f"b{b}": net.bus.at[b, "name"] for b in net.bus.index}
    for x in br:
        x["f"], x["t"] = x["f"], x["t"]
    src = []
    for e in net.ext_grid.index:
        b = int(net.ext_grid.at[e, "bus"])
        r = net.res_ext_grid.loc[e]
        pos[f"e{e}"] = [pos[nm(b)][0] - 80, pos[nm(b)][1]]
        src.append({"id": f"e{e}", "k": "ext", "n": net.ext_grid.at[e, "name"], "bus": nm(b), "bus_n": name_of[nm(b)],
                    "p": _n(r.p_mw, 2), "q": _n(r.q_mvar, 2), "v": _n(rb.at[b, "vm_pu"])})
    for g in net.gen.index:
        b = int(net.gen.at[g, "bus"])
        r = net.res_gen.loc[g]
        k_ = sum(1 for s_ in src if s_["k"] == "gen" and s_["bus"] == nm(b))
        pos[f"g{g}"] = [pos[nm(b)][0] + 55 * k_, pos[nm(b)][1] - 105]
        src.append({"id": f"g{g}", "k": "gen", "n": net.gen.at[g, "name"], "bus": nm(b), "bus_n": name_of[nm(b)],
                    "p": _n(r.p_mw, 2), "q": _n(r.q_mvar, 2), "v": _n(rb.at[b, "vm_pu"])})
    ld = []
    for i in net.load.index:
        b = int(net.load.at[i, "bus"])
        r = net.res_load.loc[i]
        k_ = sum(1 for l_ in ld if l_["bus"] == nm(b))
        pos[f"y{i}"] = [pos[nm(b)][0] + 60 * k_, pos[nm(b)][1] + 130]
        ld.append({"id": f"y{i}", "n": net.load.at[i, "name"], "bus": nm(b), "bus_n": name_of[nm(b)],
                   "p": _n(r.p_mw, 2), "q": _n(r.q_mvar, 2)})
    # hat/trafo etiketlerinde bara adları görünsün
    for x in br:
        x["f"], x["t"] = name_of[x["f"]], name_of[x["t"]]
        x["fi"], x["ti"] = None, None
    return {"pos": pos, "bus": bus, "br": br, "src": src, "ld": ld, "names": name_of}


def make_html(net, sayfa=False):
    d = veri(net)
    # JS tarafında dallar bara adıyla eşleşiyor: konum anahtarlarını da ada çevir
    byname = {b["n"]: b["id"] for b in d["bus"]}
    for k, v in list(byname.items()):
        d["pos"][k] = d["pos"][v]
    for s in d["src"] + d["ld"]:
        s["bus"] = s["bus_n"]
    for u in d["bus"]:
        pass
    html = TEMPLATE.replace("__DATA__", json.dumps(d, ensure_ascii=False))
    if sayfa:
        html = ('<!doctype html><html lang="tr"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
                '<title>Şebeke görünümü</title></head><body style="padding-top:env(safe-area-inset-top,0px);'
                'padding-bottom:env(safe-area-inset-bottom,0px)">' + html + '</body></html>')
    return html
