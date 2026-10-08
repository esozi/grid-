# -*- coding: utf-8 -*-
import copy
import math
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import pandapower as pp
from senaryo import build_network, metrics

G = 9.81
RHO_AIR = 1.225   # kg/m3


def buz_yuku(d_mm, m_kg_m, t_mm, rho_buz=900.0, ruzgar_ms=0.0, cd=1.0):
    """İletken başına yayılı yükler (N/m). d: iletken çapı, t: radyal buz kalınlığı.
    rho_buz: sert buz (glaze) ~900, kırağı (rime) ~300-500 kg/m3."""
    d, t = d_mm / 1000, t_mm / 1000
    m_buz = rho_buz * math.pi / 4 * ((d + 2 * t) ** 2 - d ** 2)    # kg/m
    w_iletken = m_kg_m * G
    w_buz = m_buz * G
    w_dikey = w_iletken + w_buz
    w_ruzgar = 0.5 * RHO_AIR * ruzgar_ms ** 2 * cd * (d + 2 * t)   # N/m
    w_bileske = math.hypot(w_dikey, w_ruzgar)
    return {"buz (kg/m)": m_buz, "dikey (N/m)": w_dikey,
            "rüzgar (N/m)": w_ruzgar, "bileşke (N/m)": w_bileske,
            "yük oranı": w_bileske / w_iletken}


def sarkma(w_n_m, aralik_m, h_n):
    """Parabolik yaklaşım: f = w·L²/(8·H). H sabit varsayımı alt sınırdır;
    gerçek değer için durum değişim denklemi gerekir."""
    return w_n_m * aralik_m ** 2 / (8 * h_n)


def hat_cikis_senaryosu(net, hat_adi, **opts):
    """Buzlanmadan dolayı bir hattın devre dışı kalması (N-1)."""
    n = copy.deepcopy(net)
    idx = n.line.index[n.line.name == hat_adi][0]
    n.line.at[idx, "in_service"] = False
    pp.runpp(n, numba=False, **opts)
    beslenen = n.load.bus.map(n.res_bus.vm_pu).notna()
    kayip_yuk = n.load.p_mw[~beslenen].sum()
    sonuc = metrics(n, **opts)
    sonuc["Beslenemeyen yük (MW)"] = round(float(kayip_yuk), 2)
    return sonuc


def n1_tarama(net, vmin=0.95, yuk_sinir=100.0, **opts):
    """Her hattı sırayla devre dışı bırakıp sonucu tablolar."""
    rows = []
    for idx in net.line.index:
        ad = net.line.at[idx, "name"]
        try:
            r = hat_cikis_senaryosu(net, ad, **opts)
            ihlal = (r["Beslenemeyen yük (MW)"] > 0 or r["Vmin (pu)"] < vmin
                     or r["Hat max yük (%)"] > yuk_sinir)
            rows.append({"Devre dışı hat": ad, "Vmin (pu)": r["Vmin (pu)"],
                         "Hat max yük (%)": r["Hat max yük (%)"],
                         "Beslenemeyen yük (MW)": r["Beslenemeyen yük (MW)"],
                         "Kayıp (MW)": r["Kayıp (MW)"],
                         "Durum": "İhlal" if ihlal else "Güvenli"})
        except Exception:
            rows.append({"Devre dışı hat": ad, "Durum": "Hesaplanamadı"})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    # 243-AL1/39-ST1A için yaklaşık değerler (katalogdan doğrulayın)
    d_mm, m_kg_m, aralik, H = 21.9, 0.99, 300, 25000

    rows = {}
    for ad, t, rho, v in [("Buzsuz", 0, 900, 0), ("10 mm sert buz", 10, 900, 0),
                          ("20 mm sert buz", 20, 900, 0),
                          ("20 mm buz + 10 m/s rüzgar", 20, 900, 10)]:
        y = buz_yuku(d_mm, m_kg_m, t, rho, v)
        y["sarkma (m), H sabit"] = sarkma(y["bileşke (N/m)"], aralik, H)
        rows[ad] = {k: round(v_, 2) for k, v_ in y.items()}
    print(pd.DataFrame(rows).to_string())

    print("\nHat devre dışı (N-1):")
    for ad, kw in [("Radyal", {}), ("Halka", {"ring": True})]:
        print(ad, hat_cikis_senaryosu(build_network(**kw), "L2"))
