# -*- coding: utf-8 -*-
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import pandapower as pp
import pandapower.shortcircuit as sc

# Trafo bağlantı grubu -> faz kayması (derece)
SHIFT = {"YNd5": 150, "YNd11": 330, "Dyn11": 330, "Dyn5": 150, "YNyn0": 0}


def build_network(n_bus=6, seg_km=10, line_type="243-AL1/39-ST1A 110.0",
                  gen_p_mw=60, gen_vm=1.01, load_mw=30, load_mvar=12,
                  gen_bus=2, ring=False, trafo_group=None, topology="radyal",
                  trafo_type="63 MVA 110/20 kV", trafo_paralel=1, tap_pos=0,
                  kol_yuk_mw=0.0):
    """topology: radyal | halka | dal-budak (ana hat + kollar)."""
    if ring:
        topology = "halka"
    net = pp.create_empty_network(name="Interconnected")
    m = min(n_bus, max(3, (n_bus + 1) // 2)) if topology == "dal-budak" else n_bus
    bus = [pp.create_bus(net, vn_kv=110, name=f"B{i}") for i in range(n_bus)]

    step = min(150, 640 / max(1, m - 1))
    gx = [130 + min(i, m - 1) * step for i in range(n_bus)]
    gy = [190.0] * n_bus
    edges = [(i, i + 1) for i in range(m - 1)]
    for j in range(n_bus - m):                       # kollar
        k = m + j
        trunk, lvl = 1 + (j % (m - 1)), j // (m - 1)
        edges.append((trunk if lvl == 0 else k - (m - 1), k))
        gx[k] = gx[trunk] + 45 + 45 * lvl
        gy[k] = 190 + 80 * (lvl + 1)
    if topology == "halka":
        edges.append((n_bus - 1, 0))

    pp.create_ext_grid(net, bus[0], vm_pu=1.0, name="Interkonnekte sebeke",
                       s_sc_max_mva=5000, s_sc_min_mva=3000,
                       rx_max=0.1, rx_min=0.1, r0x0_max=0.1, x0x_max=1.0)
    for i, (a_, b_) in enumerate(edges):
        ad = "L_halka" if (topology == "halka" and i == len(edges) - 1) else f"L{i}"
        pp.create_line(net, bus[a_], bus[b_], length_km=seg_km,
                       std_type=line_type, name=ad)

    gen_bus = min(gen_bus, m - 1)
    pp.create_gen(net, bus[gen_bus], p_mw=gen_p_mw, vm_pu=gen_vm, name="Gen",
                  sn_mva=100, vn_kv=110, xdss_pu=0.2, rdss_ohm=0.0, cos_phi=0.85)
    if kol_yuk_mw > 0:
        for k in range(m, n_bus):
            pp.create_load(net, bus[k], p_mw=kol_yuk_mw, q_mvar=0.4 * kol_yuk_mw,
                           name=f"Kol yuku B{k}")

    d20 = pp.create_bus(net, vn_kv=20, name="D20")
    t = pp.create_transformer(net, bus[m - 1], d20, std_type=trafo_type,
                              name="Trafo", parallel=int(trafo_paralel))
    net.trafo.at[t, "tap_pos"] = tap_pos
    if trafo_group:
        net.trafo.at[t, "vector_group"] = trafo_group
        net.trafo.at[t, "shift_degree"] = SHIFT[trafo_group]
    pp.create_load(net, d20, p_mw=load_mw, q_mvar=load_mvar, name="Yuk")
    net.bus["gx"] = gx + [130 + (m - 1) * step + 170]
    net.bus["gy"] = gy + [190.0]
    return net


def metrics(net, **opts):
    pp.runpp(net, numba=False, **opts)
    kayip = net.res_line.pl_mw.sum() + net.res_trafo.pl_mw.sum()
    yuk = net.load.p_mw.sum()
    return {
        "Vmin (pu)": round(float(net.res_bus.vm_pu.min()), 4),
        "Vmax (pu)": round(float(net.res_bus.vm_pu.max()), 4),
        "Hat max yük (%)": round(float(net.res_line.loading_percent.max()), 1),
        "Trafo yük (%)": round(float(net.res_trafo.loading_percent.max()), 1),
        "Kayıp (MW)": round(float(kayip), 3),
        "Kayıp (% yük)": round(float(100 * kayip / yuk), 2),
        "Slack P (MW)": round(float(net.res_ext_grid.p_mw.sum()), 2),
        "İterasyon": int(net._ppc["iterations"]) if net._ppc else 0,
    }


def add_zero_sequence(net):
    """Hat std tipinde sıfır bileşen yoksa tipik oranlarla doldur (katalogdan değiştir)."""
    for c, f in [("r0_ohm_per_km", 3.0), ("x0_ohm_per_km", 3.0)]:
        if c not in net.line.columns or net.line[c].isna().any():
            base = "r_ohm_per_km" if c.startswith("r0") else "x_ohm_per_km"
            net.line[c] = net.line[base] * f
    if "c0_nf_per_km" not in net.line.columns or net.line["c0_nf_per_km"].isna().any():
        net.line["c0_nf_per_km"] = 0.6 * net.line["c_nf_per_km"]
    # Trafo sıfır bileşen verisi (trafo etiket/test raporundan girilmeli)
    # kısa devre modülü grubu faz numarasız ister (YNd, Dyn, YNyn); kayma shift_degree'de
    net.trafo["vector_group"] = net.trafo["vector_group"].str.rstrip("0123456789")
    net.trafo["vk0_percent"] = net.trafo["vk_percent"]
    net.trafo["vkr0_percent"] = net.trafo["vkr_percent"]
    net.trafo["mag0_percent"] = 100
    net.trafo["mag0_rx"] = 0
    net.trafo["si0_hv_partial"] = 0.9


def fault_table(net, case="max"):
    add_zero_sequence(net)
    rows = {}
    for f in ["3ph", "2ph", "1ph"]:
        sc.calc_sc(net, fault=f, case=case)
        rows[f] = net.res_bus_sc.ikss_ka.round(2)
    df = pd.DataFrame(rows)
    df.insert(0, "Bara", net.bus.name)
    return df


def compare(scenarios):
    out = {}
    for ad, kw in scenarios.items():
        out[ad] = metrics(build_network(**kw))
    return pd.DataFrame(out)


if __name__ == "__main__":
    senaryolar = {
        "Baz": {},
        "Gen 100 MW": {"gen_p_mw": 100},
        "Gen 0 MW": {"gen_p_mw": 0},
        "Hat 490 mm²": {"line_type": "490-AL1/64-ST1A 110.0"},
        "Halka": {"ring": True},
        "10 bara": {"n_bus": 10},
        "Yük x1.5": {"load_mw": 45, "load_mvar": 18},
    }
    print(compare(senaryolar).to_string())

    for g in ["YNd5", "Dyn11", "YNyn0"]:
        print("\nTrafo", g)
        print(fault_table(build_network(trafo_group=g)).to_string(index=False))
