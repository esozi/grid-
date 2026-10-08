# -*- coding: utf-8 -*-
"""Serbest şebeke modeli: eleman tabloları <-> pandapower (PowerFactory 'veri yöneticisi' benzeri)."""
import io
import json
import pandas as pd
import pandapower as pp

from senaryo import SHIFT

COLS = {
    "buses": ["name", "vn_kv", "x", "y"],
    "lines": ["name", "from_bus", "to_bus", "length_km", "std_type"],
    "trafos": ["name", "hv_bus", "lv_bus", "std_type", "vector_group", "tap_pos", "parallel"],
    "gens": ["name", "bus", "p_mw", "vm_pu"],
    "ext": ["name", "bus", "vm_pu", "s_sc_max_mva", "s_sc_min_mva"],
    "loads": ["name", "bus", "p_mw", "q_mvar"],
}
BASLIK = {"buses": "Baralar", "lines": "Hatlar", "trafos": "Trafolar", "gens": "Generatörler",
          "ext": "Dış şebeke", "loads": "Yükler"}

_t = pp.create_empty_network()
LINE_TYPES = sorted(pp.available_std_types(_t, "line").index)
TRAFO_TYPES = sorted(pp.available_std_types(_t, "trafo").index)


def net_to_project(net):
    nm = net.bus.name
    P = {
        "buses": pd.DataFrame({"name": nm.values, "vn_kv": net.bus.vn_kv.values,
                               "x": net.bus.gx.values.astype(float), "y": net.bus.gy.values.astype(float)}),
        "lines": pd.DataFrame({"name": net.line.name.values, "from_bus": net.line.from_bus.map(nm).values,
                               "to_bus": net.line.to_bus.map(nm).values, "length_km": net.line.length_km.values,
                               "std_type": net.line.std_type.values}),
        "trafos": pd.DataFrame({"name": net.trafo.name.values, "hv_bus": net.trafo.hv_bus.map(nm).values,
                                "lv_bus": net.trafo.lv_bus.map(nm).values, "std_type": net.trafo.std_type.values,
                                "vector_group": net.trafo.vector_group.values,
                                "tap_pos": net.trafo.tap_pos.astype(int).values,
                                "parallel": net.trafo.parallel.astype(int).values}),
        "gens": pd.DataFrame({"name": net.gen.name.values, "bus": net.gen.bus.map(nm).values,
                              "p_mw": net.gen.p_mw.values, "vm_pu": net.gen.vm_pu.values}),
        "ext": pd.DataFrame({"name": net.ext_grid.name.values, "bus": net.ext_grid.bus.map(nm).values,
                             "vm_pu": net.ext_grid.vm_pu.values,
                             "s_sc_max_mva": net.ext_grid.s_sc_max_mva.values,
                             "s_sc_min_mva": net.ext_grid.s_sc_min_mva.values}),
        "loads": pd.DataFrame({"name": net.load.name.values, "bus": net.load.bus.map(nm).values,
                               "p_mw": net.load.p_mw.values, "q_mvar": net.load.q_mvar.values}),
    }
    return P


def _temiz(df, k):
    df = df.copy()
    for c in COLS[k]:
        if c not in df.columns:
            df[c] = None
    df = df[COLS[k]]
    df = df[df["name"].notna() & (df["name"].astype(str).str.strip() != "")]
    return df.reset_index(drop=True)


def dogrula(P):
    hata = []
    P = {k: _temiz(P[k], k) for k in COLS}
    bus = set(P["buses"].name)
    if len(bus) != len(P["buses"]):
        hata.append("Bara adları benzersiz olmalı.")
    if P["ext"].empty:
        hata.append("En az bir dış şebeke (slack) gerekli.")
    for k, cols in [("lines", ["from_bus", "to_bus"]), ("trafos", ["hv_bus", "lv_bus"]),
                    ("gens", ["bus"]), ("ext", ["bus"]), ("loads", ["bus"])]:
        for c in cols:
            kotu = set(P[k][c].dropna()) - bus
            if kotu or P[k][c].isna().any():
                hata.append(f"{BASLIK[k]}: '{c}' sütununda tanımsız veya boş bara var {sorted(map(str, kotu))}.")
    for k in ["lines", "trafos", "gens", "ext", "loads"]:
        if P[k].name.duplicated().any():
            hata.append(f"{BASLIK[k]}: eleman adları benzersiz olmalı.")
    vc = pd.concat([P["gens"][["bus", "vm_pu"]], P["ext"][["bus", "vm_pu"]]])
    for b_, grp in vc.groupby("bus"):
        if grp.vm_pu.nunique() > 1:
            hata.append(f"{b_} barasındaki generatör/dış şebeke gerilim ayarları (vm_pu) aynı olmalı.")
    if (P["lines"].length_km.fillna(0) <= 0).any():
        hata.append("Hat uzunlukları 0'dan büyük olmalı.")
    return hata


def project_to_net(P):
    P = {k: _temiz(P[k], k) for k in COLS}
    h = dogrula(P)
    if h:
        raise ValueError("; ".join(h))
    net = pp.create_empty_network(name="Proje")
    idx = {}
    for r in P["buses"].itertuples():
        idx[r.name] = pp.create_bus(net, vn_kv=float(r.vn_kv), name=r.name)
    net.bus["gx"] = [float(v) for v in P["buses"].x]
    net.bus["gy"] = [float(v) for v in P["buses"].y]
    for r in P["ext"].itertuples():
        pp.create_ext_grid(net, idx[r.bus], vm_pu=float(r.vm_pu), name=r.name,
                           s_sc_max_mva=float(r.s_sc_max_mva), s_sc_min_mva=float(r.s_sc_min_mva),
                           rx_max=0.1, rx_min=0.1, r0x0_max=0.1, x0x_max=1.0)
    for r in P["lines"].itertuples():
        pp.create_line(net, idx[r.from_bus], idx[r.to_bus], length_km=float(r.length_km),
                       std_type=r.std_type, name=r.name)
    for r in P["trafos"].itertuples():
        t = pp.create_transformer(net, idx[r.hv_bus], idx[r.lv_bus], std_type=r.std_type, name=r.name,
                                  parallel=int(r.parallel or 1))
        net.trafo.at[t, "tap_pos"] = int(r.tap_pos or 0)
        if r.vector_group in SHIFT:
            net.trafo.at[t, "vector_group"] = r.vector_group
            net.trafo.at[t, "shift_degree"] = SHIFT[r.vector_group]
    for r in P["gens"].itertuples():
        pp.create_gen(net, idx[r.bus], p_mw=float(r.p_mw), vm_pu=float(r.vm_pu), name=r.name,
                      sn_mva=100, vn_kv=float(net.bus.at[idx[r.bus], "vn_kv"]),
                      xdss_pu=0.2, rdss_ohm=0.0, cos_phi=0.85)
    for r in P["loads"].itertuples():
        pp.create_load(net, idx[r.bus], p_mw=float(r.p_mw), q_mvar=float(r.q_mvar), name=r.name)
    return net


def proje_yaz(P):
    d = {k: _temiz(P[k], k).to_dict("records") for k in COLS}
    return json.dumps(d, ensure_ascii=False, indent=1, default=float)


def proje_oku(b):
    d = json.loads(b if isinstance(b, str) else b.decode("utf-8"))
    return {k: pd.DataFrame(d.get(k, []), columns=COLS[k]) for k in COLS}
