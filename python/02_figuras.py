"""Genera todas las figuras del artículo (PNG 300 dpi) a partir de las salidas de 01_resultados.py.
Uso: python 02_figuras.py --datos <carpeta_csv> --gpkg <alertas_con_distancia.gpkg> --limites <gadm41_PER_1.json>
                          --resultados <carpeta de 01_resultados.py>
"""
import argparse, json, pickle, warnings
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
warnings.filterwarnings("ignore")

ap = argparse.ArgumentParser()
for a in ["datos", "gpkg", "limites", "resultados"]: ap.add_argument(f"--{a}", required=True)
args = ap.parse_args()
D, RES = Path(args.datos), Path(args.resultados); FIG = RES / "figuras"; FIG.mkdir(exist_ok=True)
R = json.load(open(RES / "resultados.json", encoding="utf-8")); M = pickle.load(open(RES / "modelo_salidas.pkl", "rb"))

# ---- estilo (paleta categórica validada: lightness, croma y separación CVD) ----
INK, INK2, MUTED, GRID, BASE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
CL = ['D1_agricultura', 'D2b_mineria', 'D3_suelo_expuesto', 'D4_regeneracion', 'D5_bosque']
COL = dict(zip(CL, ["#eda100", "#6250d6", "#e87ba4", "#1baf7a", "#008300"]))
LAB = dict(zip(CL, ["D1 Agricultura", "D2 Minería", "D3 Suelo expuesto", "D4 Regeneración", "D5 Bosque"]))
SEQ = "#2a78d6"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": BASE, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
                     "legend.frameon": False, "figure.dpi": 100, "savefig.dpi": 300, "savefig.bbox": "tight",
                     "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlecolor": INK})
def save(fig, n): fig.savefig(FIG / f"fig{n:02d}.png", facecolor="white"); plt.close(fig); print("fig", n)
def leyenda_destinos(ax, **kw):
    ax.legend(handles=[Patch(color=COL[c], label=LAB[c]) for c in CL], **kw)

T = pd.read_csv(D / "tabla_maestra_final.csv"); A = pd.read_csv(D / "alertas_con_trayectoria.csv")
S = pd.read_csv(D / "Dataset_DeforestacionAnp_SERNANP.csv"); S = S[S.CONFIABILIDAD == "ALTO"]
G = gpd.read_file(args.gpkg); G['alert_d'] = G.alert_d.astype(T.alert_d.dtype)
G = G.to_crs(32718); G['geometry'] = G.geometry.centroid
L = gpd.read_file(args.limites).to_crs(32718)
pred = pd.read_csv(RES / "tablas/predicciones_2024_2025.csv")

# ---------- Fig 1: área de estudio ----------
fig, ax = plt.subplots(figsize=(6.5, 7.5))
L.plot(ax=ax, color="#f4f3ef", edgecolor="#9a9890", linewidth=0.5)
g = G.merge(T[['alert_d', 'destino']], on='alert_d', how='inner')
g24 = G[G.alert_d.isin(pred.alert_d)]
g24.plot(ax=ax, color="#b9b7b0", markersize=1.2, alpha=0.6)
for c in CL[::-1]: g[g.destino == c].plot(ax=ax, color=COL[c], markersize=1.6 if c != 'D2b_mineria' else 2.5)
xmin, ymin, xmax, ymax = L.total_bounds; ax.set_xlim(xmin - 2e4, xmax + 2e4); ax.set_ylim(ymin - 2e4, ymax + 2e4)
for _, r in L.iterrows():
    p = r.geometry.representative_point(); ax.text(p.x, p.y, r.NAME_1.replace("MadredeDios", "Madre de Dios").replace("SanMartín", "San Martín")
                                                   .replace("LaLibertad", "La Libertad").replace("LimaProvince", ""), fontsize=5.5, color=MUTED, ha="center")
ax.set_axis_off()
h = [Line2D([], [], marker='o', ls='', color=COL[c], label=LAB[c] + " (T+1)") for c in CL] + \
    [Line2D([], [], marker='o', ls='', color="#b9b7b0", label="Alertas 2024–2025 (sin T+1)")]
ax.legend(handles=h, loc="lower left", fontsize=7, title="Alertas 2021–2023 (n = 21 870)", title_fontsize=7.5)
ax.plot([xmax - 30e4, xmax - 10e4], [ymin - 1e4] * 2, color=INK, lw=2); ax.text(xmax - 20e4, ymin + 0.5e4, "200 km", ha="center", fontsize=7)
ax.annotate("N", xy=(xmax - 5e4, ymax - 4e4), xytext=(xmax - 5e4, ymax - 14e4), ha="center", fontsize=9,
            arrowprops=dict(arrowstyle="-|>", color=INK))
save(fig, 1)

# ---------- Fig 2: alertas por año y por departamento ----------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.6), gridspec_kw=dict(width_ratios=[1, 1.4]))
yrs = [2021, 2022, 2023, 2024, 2025]
ana = T.ani_lrt.value_counts().reindex(yrs, fill_value=0).values
tot = A.ani_lrt.value_counts().reindex(yrs).values
a1.bar(yrs, ana, color=SEQ, width=0.6, label="Conjunto analítico")
a1.bar(yrs, tot - ana, bottom=ana, color="#b7d3f6", width=0.6, edgecolor="white", linewidth=1, label="Excluidas / sin T+1")
for x, v in zip(yrs, tot): a1.text(x, v + 150, f"{v:,}".replace(",", " "), ha="center", fontsize=7.5, color=INK2)
a1.set_title("(a) Alertas verificadas por año"); a1.set_ylabel("N.º de alertas"); a1.legend(fontsize=7.5, loc="upper left"); a1.grid(axis="x", visible=False)
dp = pd.Series(R["n_por_dpto_total"]).sort_values()
a2.barh(dp.index, dp.values, color=SEQ, height=0.6)
for i, v in enumerate(dp.values): a2.text(v + 100, i, f"{v:,}".replace(",", " "), va="center", fontsize=7, color=INK2)
a2.set_title("(b) Alertas por departamento (2021–2025)"); a2.set_xlabel("N.º de alertas"); a2.grid(axis="y", visible=False)
fig.tight_layout(); save(fig, 2)

# ---------- Fig 3: destino por departamento ----------
dep = M["dep"].sort_values("D1_agricultura")
fig, ax = plt.subplots(figsize=(7.5, 4.2)); left = np.zeros(len(dep))
for c in CL:
    v = dep.get(c, pd.Series(0, index=dep.index)).values
    ax.barh(dep.index, v, left=left, color=COL[c], edgecolor="white", linewidth=1, height=0.7, label=LAB[c]); left += v
for i, (d, r) in enumerate(dep.iterrows()): ax.text(101, i, f"n = {int(r.n):,}".replace(",", " "), va="center", fontsize=7, color=INK2)
ax.set_xlim(0, 100); ax.set_xlabel("% de alertas (T+1)"); ax.grid(axis="y", visible=False)
leyenda_destinos(ax, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.13), fontsize=7)
save(fig, 3)

# ---------- Fig 4: ANP y TI (consolidación con IC Wilson) ----------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.4), sharex=True)
anp_lab = {'dentro_intangible': 'ANP intangible', 'dentro_uso_directo': 'ANP uso directo', 'buffer_5km': 'Buffer 0–5 km',
           'buffer_10km': 'Buffer 5–10 km', 'fuera_anp': 'Fuera de ANP'}
t5 = R["T5"]; ks = list(anp_lab)[::-1]
for i, k in enumerate(ks):
    v = t5[k]; a1.errorbar(v["cons"], i, xerr=[[v["cons"] - v["cons_IC"][0]], [v["cons_IC"][1] - v["cons"]]], fmt="o", color=COL['D1_agricultura'], ms=6, capsize=3, lw=1.2)
    a1.errorbar(v["rec"], i, xerr=[[v["rec"] - v["rec_IC"][0]], [v["rec_IC"][1] - v["rec"]]], fmt="s", color=COL['D5_bosque'], ms=5, capsize=3, lw=1.2)
    a1.text(101, i, f"n = {v['n']:,}".replace(",", " "), va="center", fontsize=7, color=INK2)
a1.set_yticks(range(len(ks))); a1.set_yticklabels([anp_lab[k] for k in ks]); a1.set_title("(a) Categoría de ANP"); a1.set_xlim(0, 100)
from statsmodels.stats.proportion import proportion_confint
ti_lab = {'ti_titulada': 'TI titulada', 'ti_en_proceso': 'TI en proceso', 'fuera_ti': 'Fuera de TI'}
for i, k in enumerate(list(ti_lab)[::-1]):
    g_ = T[T.ti_final == k]; n = len(g_)
    for cls, mk, col in [(['D1_agricultura', 'D2b_mineria'], "o", COL['D1_agricultura']), (['D4_regeneracion', 'D5_bosque'], "s", COL['D5_bosque'])]:
        kk = g_.destino.isin(cls).sum(); lo, hi = proportion_confint(kk, n, method='wilson'); p = 100 * kk / n
        a2.errorbar(p, i, xerr=[[p - 100 * lo], [100 * hi - p]], fmt=mk, color=col, ms=6 if mk == "o" else 5, capsize=3, lw=1.2)
    a2.text(101, i, f"n = {n:,}".replace(",", " "), va="center", fontsize=7, color=INK2)
a2.set_yticks(range(3)); a2.set_yticklabels(list(ti_lab.values())[::-1]); a2.set_title("(b) Territorio indígena")
for a in (a1, a2): a.set_xlabel("% de alertas (IC 95 % Wilson)"); a.grid(axis="y", visible=False)
fig.legend(handles=[Line2D([], [], marker="o", ls="", color=COL['D1_agricultura'], label="Consolidación (D1 + D2)"),
                    Line2D([], [], marker="s", ls="", color=COL['D5_bosque'], label="Recuperación / IESA (D4 + D5)")],
           loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.06), fontsize=8)
fig.tight_layout(); save(fig, 4)

# ---------- Fig 5: SERNANP zonificación ----------
zn = S.groupby("ZONIFI_ANP").AREA_DEFO.agg(["sum", "mean", "count"])
zn = zn[zn["count"] >= 10].sort_values("sum")
zn.index = [z.replace("ZONA DE ", "").replace("ZONA ", "").capitalize() for z in zn.index]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
a1.barh(zn.index, zn["sum"], color=SEQ, height=0.6); a1.set_title("(a) Área deforestada total (ha)")
a2.barh(zn.index, zn["mean"], color="#1c5cab", height=0.6); a2.set_title("(b) Intensidad media (ha/evento)")
for a, col, fmt in [(a1, "sum", "{:,.0f}"), (a2, "mean", "{:.2f}")]:
    for i, v in enumerate(zn[col]): a.text(v, i, " " + fmt.format(v).replace(",", " "), va="center", fontsize=7, color=INK2)
    a.grid(axis="y", visible=False)
fig.tight_layout(); save(fig, 5)

# ---------- Fig 6: SERNANP tendencia por categoría ----------
ct = S.pivot_table(index="ANIO_REPORTE", columns="CATEGORIA", values="AREA_DEFO", aggfunc="sum")
ct = ct[[c for c in ["RESERVA COMUNAL", "BOSQUE DE PROTECCIÓN", "RESERVA NACIONAL", "PARQUE NACIONAL", "ZONAS RESERVADAS"] if c in ct]]
cols6 = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
fig, ax = plt.subplots(figsize=(6.5, 3.6))
ylab = ct.iloc[-1].sort_values(); pos = {}; last = -1e9
for c, v in ylab.items(): pos[c] = max(v, last + 85); last = pos[c]
for c, col in zip(ct.columns, cols6):
    ax.plot(ct.index, ct[c], marker="o", color=col, lw=2, ms=7, markeredgecolor="white", markeredgewidth=2)
    ax.text(2023.08, pos[c], c.capitalize(), va="center", fontsize=7.5, color=INK2)
ax.set_xticks([2021, 2022, 2023]); ax.set_xlim(2020.8, 2023.9); ax.set_ylabel("Área deforestada (ha)"); ax.grid(axis="x", visible=False)
save(fig, 6)

# ---------- Fig 7: minería en RN Tambopata ----------
m = S[S.DEFO_CAUSA == "MINERIA"].copy(); m["t"] = pd.to_datetime(dict(year=m.ANIO_REPORTE, month=m.MES_IMAG, day=1))
mm = m.groupby("t").AREA_DEFO.sum().reindex(pd.date_range("2021-01-01", "2023-12-01", freq="MS"), fill_value=0)
fig = plt.figure(figsize=(9, 5.4)); gs = fig.add_gridspec(2, 2, height_ratios=[1.1, 1])
a1 = fig.add_subplot(gs[0, :]); a1.bar(mm.index, mm.values, width=20, color=COL['D2b_mineria'])
pk = mm.idxmax(); a1.annotate(f"{mm.max():.2f} ha ({pk:%m/%Y})", xy=(pk, mm.max()), xytext=(-90, -5), textcoords="offset points", fontsize=7.5, color=INK2,
                             arrowprops=dict(arrowstyle="-", color=MUTED))
ya = m.groupby("ANIO_REPORTE").AREA_DEFO.sum()
a1.set_title("(a) Área mensual deforestada por minería (ha) — anual: " + " · ".join(f"{k}: {v:.2f} ha" for k, v in ya.items()))
a1.grid(axis="x", visible=False)
a2 = fig.add_subplot(gs[1, 0]); z = m.groupby("ZONIFI_ANP").AREA_DEFO.sum().sort_values()
z.index = [s.replace("ZONA DE ", "").capitalize() for s in z.index]
a2.barh(z.index, z.values, color=COL['D2b_mineria'], height=0.55)
for i, v in enumerate(z.values): a2.text(v, i, f" {v:.2f} ha ({100*v/z.sum():.1f} %)", va="center", fontsize=7, color=INK2)
a2.set_xlim(0, z.max() * 1.6); a2.set_title("(b) Por zonificación interna"); a2.grid(axis="y", visible=False)
a3 = fig.add_subplot(gs[1, 1]); b = m.groupby("TIPO_BOSQUE").AREA_DEFO.sum()
a3.barh(["Bosque " + s.lower() for s in b.index], b.values, color=[COL['D5_bosque'], "#1baf7a"][:len(b)], height=0.5)
for i, v in enumerate(b.values): a3.text(v, i, f" {v:.2f} ha ({100*v/b.sum():.1f} %)", va="center", fontsize=7, color=INK2)
a3.set_xlim(0, b.max() * 1.6); a3.set_title("(c) Por tipo de bosque afectado"); a3.grid(axis="y", visible=False)
fig.tight_layout(); save(fig, 7)

# ---------- Fig 8: ROC ----------
fig, ax = plt.subplots(figsize=(4.8, 4.4))
for c in CL:
    fpr, tpr, _ = M["roc"][c]; ax.plot(fpr, tpr, color=COL[c], lw=2, label=f"{LAB[c]} (AUC = {M['auc'][c]:.3f})")
ax.plot([0, 1], [0, 1], color=MUTED, lw=1, ls="--")
ax.set_xlabel("Tasa de falsos positivos"); ax.set_ylabel("Tasa de verdaderos positivos")
ax.set_title(f"AUC macro = {R['AUC_macro']:.3f}"); ax.legend(fontsize=7, loc="lower right"); save(fig, 8)

# ---------- Fig 9: matriz de confusión ----------
cm = M["cm"]; cmn = cm / cm.sum(1, keepdims=True) * 100
fig, ax = plt.subplots(figsize=(5.4, 4.4)); im = ax.imshow(cmn, cmap="Blues", vmin=0, vmax=100)
for i in range(5):
    for j in range(5): ax.text(j, i, f"{cmn[i, j]:.1f} %\n({cm[i, j]})", ha="center", va="center", fontsize=7, color="white" if cmn[i, j] > 55 else INK)
short = ["D1", "D2", "D3", "D4", "D5"]
ax.set_xticks(range(5)); ax.set_xticklabels(short); ax.set_yticks(range(5)); ax.set_yticklabels([LAB[c] for c in CL])
ax.set_xlabel("Clase predicha"); ax.set_ylabel("Clase observada"); ax.grid(False)
fig.colorbar(im, ax=ax, fraction=0.046, label="% de la clase observada"); save(fig, 9)

# ---------- Fig 10: diagrama de fiabilidad ----------
fig, ax = plt.subplots(figsize=(4.8, 4.4))
for c in CL:
    pt, pp = M["rel"][c]; ax.plot(pp, pt, marker="o", color=COL[c], lw=2, ms=4, label=f"{LAB[c]} (Brier = {R['Brier'][c]:.3f})")
ax.plot([0, 1], [0, 1], color=MUTED, lw=1, ls="--"); ax.set_xlabel("Probabilidad predicha media"); ax.set_ylabel("Frecuencia observada")
ax.legend(fontsize=7, loc="upper left"); save(fig, 10)

# ---------- Fig 11: SHAP ----------
sc = M["shap_clase"].head(12).iloc[::-1]
nice = lambda s: (s.replace("tip_lrt_", "Presión: ").replace("dprtmnt_", "Dpto: ").replace("anp_categoria_", "ANP: ").replace("ti_final_", "TI: ")
                  .replace("clase_T1_", "T−1: ").replace("log_are", "log(área)").replace("log_dist_via", "log(dist. vía)").replace("ani_lrt", "Año de alerta")
                  .replace("carretera_cerca", "Vía ≤ 2 km").replace("ilegal_mining", "minería ilegal").replace("agriculture", "agricultura"))
fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.6))
left = np.zeros(len(sc))
for c in CL:
    a1.barh([nice(i) for i in sc.index], sc[c].values, left=left, color=COL[c], edgecolor="white", linewidth=1, height=0.7, label=LAB[c]); left += sc[c].values
a1.set_xlabel("Media |SHAP| (suma sobre clases)"); a1.set_title("(a) Importancia global"); a1.grid(axis="y", visible=False); leyenda_destinos(a1, fontsize=6.5, loc="lower right")
sv, Xs = M["shap_sv"], M["shap_X"]; order = np.argsort(np.abs(sv).mean(0))[::-1][:12][::-1]
rng = np.random.default_rng(42)
for k, j in enumerate(order):
    v = Xs.iloc[:, j].values; vn = (v - v.min()) / (v.max() - v.min() + 1e-9)
    a2.scatter(sv[:, j], k + rng.uniform(-0.3, 0.3, len(v)), c=vn, cmap="coolwarm", s=3, alpha=0.6, linewidths=0)
a2.set_yticks(range(len(order))); a2.set_yticklabels([nice(Xs.columns[j]) for j in order]); a2.axvline(0, color=MUTED, lw=0.8)
a2.set_xlabel("Valor SHAP para D1 Agricultura"); a2.set_title("(b) Efecto sobre P(D1)"); a2.grid(axis="y", visible=False)
sm_ = plt.cm.ScalarMappable(cmap="coolwarm"); fig.colorbar(sm_, ax=a2, fraction=0.04, ticks=[0, 1]).ax.set_yticklabels(["bajo", "alto"])
fig.tight_layout(); save(fig, 11)

# ---------- Fig 12: evolución alertas 2021 ----------
ev = M["evo"]; fig, ax = plt.subplots(figsize=(6.5, 3.4)); left = np.zeros(3); labs = ["T+1 (2022)", "T+2 (2023)", "T+3 (2024)"]
for c in CL + ['otros']:
    v = np.array([ev[t].get(c, 0) for t in ["T1", "T2", "T3"]])
    ax.barh(labs, v, left=left, color=COL.get(c, "#c3c2b7"), edgecolor="white", linewidth=1, height=0.6, label=LAB.get(c, "Otras clases"))
    for i in range(3):
        if v[i] > 6: ax.text(left[i] + v[i] / 2, i, f"{v[i]:.1f} %", ha="center", va="center", fontsize=7.5, color=INK if c == 'D1_agricultura' else "white")
    left += v
ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel(f"% de alertas 2021 (n = {R['n_2021_analitico']:,})".replace(",", " ")); ax.grid(axis="y", visible=False)
ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.2), fontsize=7); save(fig, 12)

# ---------- Fig 13: trayectorias por ANP y TI ----------
R21 = M["R21"]; tcol = {"Consolidación rápida": COL['D1_agricultura'], "Recuperación sostenida": COL['D5_bosque'], "Otras": "#e87ba4"}
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.2))
for a, var, lab, title in [(a1, "anp_categoria", anp_lab, "(a) Categoría de ANP"), (a2, "ti_final", ti_lab, "(b) Territorio indígena")]:
    ctab = pd.crosstab(R21[var], R21.tray3, normalize="index").mul(100).reindex(list(lab)[::-1]); nn = R21[var].value_counts()
    left = np.zeros(len(ctab))
    for t, col in tcol.items():
        v = ctab.get(t, pd.Series(0, index=ctab.index)).fillna(0).values
        a.barh([lab[k] for k in ctab.index], v, left=left, color=col, edgecolor="white", linewidth=1, height=0.65, label=t); left += v
    for i, k in enumerate(ctab.index): a.text(101, i, f"n = {nn.get(k, 0):,}".replace(",", " "), va="center", fontsize=7, color=INK2)
    a.set_xlim(0, 100); a.set_xlabel("% de alertas 2021"); a.set_title(title); a.grid(axis="y", visible=False)
a1.legend(ncol=3, loc="upper center", bbox_to_anchor=(1.1, -0.2), fontsize=7.5); fig.tight_layout(); save(fig, 13)

# ---------- Fig 14: observado vs predicho + mapa ----------
fig = plt.figure(figsize=(10, 5.2)); gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.1])
a1 = fig.add_subplot(gs[0, 0]); rows = []
for yr in [2021, 2022, 2023]: rows.append((str(yr), T[T.ani_lrt == yr].destino.value_counts(normalize=True).mul(100)))
for yr in [2024, 2025]:
    pp_ = pred[pred.ani_lrt == yr]; rows.append((f"{yr}*", pd.Series({c: 100 * pp_[f"p_{c}"].mean() for c in CL})))
left = np.zeros(len(rows))
for c in CL:
    v = np.array([r[1].get(c, 0) for r in rows]); a1.barh([r[0] for r in rows], v, left=left, color=COL[c], edgecolor="white", linewidth=1, height=0.65, label=LAB[c]); left += v
a1.axhline(2.5, color=INK, ls="--", lw=1); a1.invert_yaxis(); a1.set_xlim(0, 100); a1.set_xlabel("% de alertas"); a1.grid(axis="y", visible=False)
a1.set_title("(a) Observado 2021–2023 y esperado 2024–2025*"); leyenda_destinos(a1, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.12), fontsize=7)
a2 = fig.add_subplot(gs[0, 1]); L.plot(ax=a2, color="#f4f3ef", edgecolor="#9a9890", linewidth=0.5)
gp = G.merge(pred[['alert_d', 'triaje']], on='alert_d')
TRI = {"alta": ("#eda100", "Alta (P ≥ 0,8)"), "intermedia": ("#e87ba4", "Intermedia (0,5–0,8)"), "baja": ("#008300", "Baja (P < 0,5)")}
for g_, (col, lab) in TRI.items(): gp[gp.triaje == g_].plot(ax=a2, color=col, markersize=1.4 if g_ == "alta" else 2.6)
a2.set_xlim(xmin + 3e5, xmax); a2.set_ylim(ymin + 4e5, ymax); a2.set_axis_off()
a2.set_title("(b) Probabilidad calibrada de consolidación, 2024–2025")
a2.legend(handles=[Line2D([], [], marker='o', ls='', color=c, label=l) for c, l in TRI.values()], loc="lower left", fontsize=7)
fig.tight_layout(); save(fig, 14)
print("OK figuras en", FIG)
