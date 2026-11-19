"""
Trayectorias post-deforestación en la Amazonía peruana (2021–2025)
Script único que reproduce TODOS los valores numéricos del artículo.

Uso:
    python 01_resultados.py --datos <carpeta_csv> --gpkg <alertas_con_distancia.gpkg> --salida <carpeta>

Entradas (carpeta --datos):
    alertas_con_trayectoria.csv      salida de gee/01 (39 649 alertas, T−1, destino T+1, Gini T+1, flags)
    tabla_maestra_final.csv          conjunto analítico 2021–2023 (21 870) con ANP, TI, vías
    alertas_2021_T2_T3.csv           salida de gee/03 (destinos T+2, T+3 de alertas 2021)
    pseudo_alertas_control.csv       salida de gee/04 (1 273 pseudo-alertas)
    predicciones_2024.csv / predicciones_2025.csv   variables explicativas de las alertas 2024–2025
    Dataset_DeforestacionAnp_SERNANP.csv            SERNANP (2024b)
Salidas: resultados.json, tablas/*.csv, modelo_salidas.pkl (para 02_figuras.py)
Semilla global = 42.
"""
import argparse, json, pickle, warnings
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd
from scipy.stats import chi2_contingency, fisher_exact
import statsmodels.api as sm
from statsmodels.stats.proportion import proportion_confint
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score, cross_val_predict
from sklearn.metrics import (balanced_accuracy_score, roc_auc_score, roc_curve, f1_score, brier_score_loss,
                             precision_recall_fscore_support, confusion_matrix)
from sklearn.neighbors import NearestNeighbors
warnings.filterwarnings("ignore")

ap = argparse.ArgumentParser()
ap.add_argument("--datos", required=True); ap.add_argument("--gpkg", required=True); ap.add_argument("--salida", required=True)
args = ap.parse_args()
D = Path(args.datos); OUT = Path(args.salida); (OUT / "tablas").mkdir(parents=True, exist_ok=True)
SEED = 42
R = {}
def rec(k, v):
    R[k] = v; print(f"{k}: {v}")
def r3(x): return float(round(x, 3))

CLASES = ['D1_agricultura', 'D2b_mineria', 'D3_suelo_expuesto', 'D4_regeneracion', 'D5_bosque']
CONS = {'D1_agricultura', 'D2b_mineria'}
REC = {'D4_regeneracion', 'D5_bosque'}

A = pd.read_csv(D / "alertas_con_trayectoria.csv")
T = pd.read_csv(D / "tabla_maestra_final.csv")
T2 = pd.read_csv(D / "alertas_2021_T2_T3.csv")
P = pd.read_csv(D / "pseudo_alertas_control.csv")
S = pd.read_csv(D / "Dataset_DeforestacionAnp_SERNANP.csv")

# =====================================================================
# 1. EMBUDO
# =====================================================================
print("\n=== 1. EMBUDO")
rec("n_total", len(A))
rec("n_por_anio", {int(k): int(v) for k, v in A.ani_lrt.value_counts().sort_index().items()})
G_all = gpd.read_file(args.gpkg, ignore_geometry=True)[['alert_d', 'ani_lrt', 'dprtmnt']]
dpt_all = G_all.dprtmnt.value_counts()
rec("n_por_dpto_total", dpt_all.to_dict())
rec("pct_Ucayali_Loreto_total", round(100 * (dpt_all['Ucayali'] + dpt_all['Loreto']) / len(G_all), 1))
s = A[A.ani_lrt <= 2023]
paso_T1 = s.flag_excluir == 1
paso_mix = (~paso_T1) & (s.flag_mixta == 1)
paso_otros = (~paso_T1) & (~paso_mix) & (s.destino == 'otros')
rec("n_2021_2023", len(s)); rec("n_2024_2025", int((A.ani_lrt >= 2024).sum()))
rec("excl_T1_no_forestal", int(paso_T1.sum()))
rec("excl_mixtos_gini_gt_0.5", int(paso_mix.sum()))
rec("excl_destino_otros", int(paso_otros.sum()))
rec("n_analitico", len(T))
assert len(s) - paso_T1.sum() - paso_mix.sum() - paso_otros.sum() == len(T)
rec("mixtos_dist_destino_%", (s[paso_mix].destino.value_counts(normalize=True) * 100).round(1).to_dict())
sens = s[(~paso_T1) & (s.destino != 'otros')]
rec("sensibilidad_incl_mixtos_n", len(sens))
rec("sensibilidad_incl_mixtos_%", (sens.destino.value_counts(normalize=True) * 100).round(1).to_dict())
rec("sensibilidad_incl_mixtos_consolidacion_%", round(100 * sens.destino.isin(CONS).mean(), 1))

# =====================================================================
# 2. DESCRIPTIVOS (Tabla 3, departamentos)
# =====================================================================
print("\n=== 2. DESCRIPTIVOS")
yC = T.destino.isin(CONS)
t3 = T.destino.value_counts().reindex(CLASES)
rec("T3_n", t3.to_dict()); rec("T3_%", (100 * t3 / len(T)).round(1).to_dict())
rec("T3_consolidacion_%", round(100 * yC.mean(), 1)); rec("T3_IESA_%", round(100 * T.destino.isin(REC).mean(), 1))
rec("T_por_anio", {int(k): int(v) for k, v in T.ani_lrt.value_counts().sort_index().items()})
dep = T.groupby('dprtmnt').destino.value_counts(normalize=True).unstack().fillna(0).mul(100).round(1)
dep['n'] = T.dprtmnt.value_counts(); dep['consolidacion'] = (dep.get('D1_agricultura', 0) + dep.get('D2b_mineria', 0)).round(1)
dep = dep.sort_values('D1_agricultura', ascending=False); dep.to_csv(OUT / "tablas/departamentos.csv")
rec("dptos", dep[['n', 'D1_agricultura', 'D2b_mineria', 'D5_bosque', 'consolidacion']].to_dict('index'))

# =====================================================================
# 3. ANP y TI (Tabla 5, OR crudos y ajustados)
# =====================================================================
print("\n=== 3. ANP / TI")
def wilson(k, n):
    lo, hi = proportion_confint(k, n, method='wilson'); return [round(100 * lo, 1), round(100 * hi, 1)]
anp_orden = ['dentro_intangible', 'dentro_uso_directo', 'buffer_5km', 'buffer_10km', 'fuera_anp']
t5 = {}
for c in anp_orden:
    g = T[T.anp_categoria == c]; n = len(g); kc = int(g.destino.isin(CONS).sum()); kr = int(g.destino.isin(REC).sum())
    t5[c] = dict(n=n, cons=round(100 * kc / n, 1), cons_IC=wilson(kc, n), rec=round(100 * kr / n, 1), rec_IC=wilson(kr, n))
rec("T5", t5)
c2, pv, dof, _ = chi2_contingency(pd.crosstab(T.anp_categoria, yC)); rec("chi2_ANP_cons", dict(chi2=r3(c2), gl=int(dof), p=float(pv)))

def or_crudo(ma, mb):
    tab = np.array([[(yC & ma).sum(), (~yC & ma).sum()], [(yC & mb).sum(), (~yC & mb).sum()]], float)
    o, p = fisher_exact(tab); se = np.sqrt((1 / tab).sum())
    return dict(OR=r3(o), IC=[r3(np.exp(np.log(o) - 1.96 * se)), r3(np.exp(np.log(o) + 1.96 * se))], p=float(p), n_a=int(ma.sum()))
dentro = T.dentro_ANP_dummy == 1
rec("OR_crudo_dentroANP", or_crudo(dentro, ~dentro))
ti_orden = ['ti_titulada', 'ti_en_proceso', 'fuera_ti']
rec("TI", {c: dict(n=int((T.ti_final == c).sum()), cons=round(100 * T.loc[T.ti_final == c, 'destino'].isin(CONS).mean(), 1)) for c in ti_orden})
fu = T.ti_final == 'fuera_ti'
rec("OR_crudo_TI_titulada", or_crudo(T.ti_final == 'ti_titulada', fu))
rec("OR_crudo_TI_proceso", or_crudo(T.ti_final == 'ti_en_proceso', fu))
c2, pv, dof, _ = chi2_contingency(pd.crosstab(T.ti_final, yC)); rec("chi2_TI_cons", dict(chi2=r3(c2), gl=int(dof), p=float(pv)))
mi = T[(T.tip_lrt == 'ilegal_mining') & (T.ti_final == 'ti_titulada')]
rec("mineria_ilegal_TI_titulada", dict(n=len(mi), cons=round(100 * mi.destino.isin(CONS).mean(), 1)))

# Regresión logística multivariable: P(consolidación)
T['presion3'] = np.select([T.tip_lrt == 'agriculture', T.tip_lrt.isin(['ilegal_mining', 'mining'])], ['agricultura', 'mineria'], 'otros')
Xl = pd.DataFrame({'dentro_ANP': dentro.astype(float),
                   'ti_titulada': (T.ti_final == 'ti_titulada').astype(float),
                   'ti_en_proceso': (T.ti_final == 'ti_en_proceso').astype(float),
                   'log_area': T.log_are, 'log_dist_via': T.log_dist_via, 'via_2km': T.carretera_cerca.astype(float),
                   'presion_mineria': (T.presion3 == 'mineria').astype(float), 'presion_otros': (T.presion3 == 'otros').astype(float),
                   'T1_formacion_natural': (T.clase_T1 != 'bosque_primario').astype(float),
                   'anio_2022': (T.ani_lrt == 2022).astype(float), 'anio_2023': (T.ani_lrt == 2023).astype(float)})
Xl = pd.concat([Xl, pd.get_dummies(T.dprtmnt, prefix='dpto').drop(columns='dpto_Ucayali').astype(float)], axis=1)
logit = sm.Logit(yC.astype(float), sm.add_constant(Xl)).fit(disp=0, method='bfgs', maxiter=2000)
ci = logit.conf_int()
orl = pd.DataFrame({'OR': np.exp(logit.params), 'IC_inf': np.exp(ci[0]), 'IC_sup': np.exp(ci[1]), 'p': logit.pvalues}).drop('const')
orl.round(4).to_csv(OUT / "tablas/odds_ratios_logit.csv")
for v in ['dentro_ANP', 'ti_titulada', 'ti_en_proceso', 'log_dist_via', 'via_2km', 'presion_mineria', 'log_area']:
    rec(f"ORaj_{v}", dict(OR=r3(orl.loc[v, 'OR']), IC=[r3(orl.loc[v, 'IC_inf']), r3(orl.loc[v, 'IC_sup'])], p=float(orl.loc[v, 'p'])))
rec("logit_pseudoR2", r3(logit.prsquared))

# =====================================================================
# 4. GRUPO CONTROL e IESA (Tabla 4) — alertas 2021 del conjunto analítico
# =====================================================================
print("\n=== 4. IESA / CONTROL")
R21 = T2[T2.alert_d.isin(T.alert_d)].copy()
rec("n_2021_analitico", len(R21)); rec("n_2021_total", len(T2))
iesa = {}
for lab, cr, cp in [('T1', 'destino', 'destino_T1'), ('T2', 'destino_T2', 'destino_T2'), ('T3', 'destino_T3', 'destino_T3')]:
    kr, nr = int(R21[cr].isin(REC).sum()), len(R21); kp, np_ = int(P[cp].isin(REC).sum()), len(P)
    c2, pv, dof, _ = chi2_contingency(np.array([[kr, nr - kr], [kp, np_ - kp]]), correction=False)
    iesa[lab] = dict(real=round(100 * kr / nr, 1), real_IC=wilson(kr, nr), control=round(100 * kp / np_, 1), control_IC=wilson(kp, np_),
                     delta=round(100 * kr / nr - 100 * kp / np_, 1), chi2=round(c2, 1), gl=int(dof), p=float(pv))
rec("T4_IESA", iesa)
rec("control_destinos_T1", P.destino_T1.value_counts().to_dict())
rec("control_rechazo_%", round(100 * (1 - len(P) / 2000), 1))

# =====================================================================
# 5. TRAYECTORIAS 2021 (Tabla 7, Fig. 14-15)
# =====================================================================
print("\n=== 5. TRAYECTORIAS")
def cl(x): return 'C' if x in CONS else 'R' if x in REC else 'S' if x == 'D3_suelo_expuesto' else 'O'
def tray(r):
    a1, a2, a3 = cl(r.destino), cl(r.destino_T2), cl(r.destino_T3)
    if a1 == 'C' and a2 == 'C': return 'Consolidación rápida'
    if a1 == 'S' and a2 == 'C': return 'Consolidación progresiva'
    if a1 == 'S' and a2 == 'S' and a3 == 'C': return 'Consolidación tardía'
    if a1 == 'R' and a2 == 'R': return 'Recuperación sostenida'
    if a1 == 'S' and a2 == 'R': return 'Recuperación post-tránsito'
    if a1 == 'C' and a2 == 'R': return 'Reversión post-uso'
    return 'Trayectoria inestable'
R21['trayectoria'] = R21.apply(tray, axis=1)
R21 = R21.merge(T[['alert_d', 'anp_categoria', 'ti_final']], on='alert_d', how='left')
t7 = R21.trayectoria.value_counts()
rec("T7", {k: dict(n=int(v), pct=round(100 * v / len(R21), 1)) for k, v in t7.items()})
rec("C3_permanece_consolidado_T1_T2_T3_%", round(100 * ((R21.destino.map(cl) == 'C') & (R21.destino_T2.map(cl) == 'C') & (R21.destino_T3.map(cl) == 'C')).mean(), 1))
evo = {}
for c, lab in [('destino', 'T1'), ('destino_T2', 'T2'), ('destino_T3', 'T3')]:
    evo[lab] = (R21[c].value_counts(normalize=True) * 100).round(1).to_dict()
rec("Fig14_evolucion", evo)
R21['tray3'] = R21.trayectoria.where(R21.trayectoria.isin(['Consolidación rápida', 'Recuperación sostenida']), 'Otras')
for v in ['anp_categoria', 'ti_final']:
    c2, pv, dof, _ = chi2_contingency(pd.crosstab(R21[v], R21.tray3))
    rec(f"chi2_tray_x_{v}", dict(chi2=r3(c2), gl=int(dof), p=float(pv)))
tray_anp = pd.crosstab(R21.anp_categoria, R21.tray3, normalize='index').mul(100).round(1)
tray_ti = pd.crosstab(R21.ti_final, R21.tray3, normalize='index').mul(100).round(1)
rec("tray_por_anp", tray_anp.to_dict('index')); rec("tray_por_ti", tray_ti.to_dict('index'))

# =====================================================================
# 6. RANDOM FOREST (modelo final, sin Gini)
# =====================================================================
print("\n=== 6. RANDOM FOREST")
CONT = ['log_are', 'log_dist_via', 'ani_lrt']
CAT = ['anp_categoria', 'ti_final', 'tip_lrt', 'dprtmnt', 'clase_T1']
BIN = ['carretera_cerca', 'dentro_ANP_dummy', 'interaccion_carretera_anp']
def matriz(d, cont=CONT, cat=CAT, binr=BIN, cols=None):
    X = pd.get_dummies(d[cont + cat + binr], columns=cat).astype(float)
    return X.reindex(columns=cols, fill_value=0.0) if cols is not None else X
def nuevo_rf(): return RandomForestClassifier(n_estimators=300, min_samples_leaf=5, class_weight='balanced', random_state=SEED, n_jobs=-1)
def auc_ovr(m, X, y):
    Pp = m.predict_proba(X); per = {c: roc_auc_score((y == c).astype(int), Pp[:, i]) for i, c in enumerate(m.classes_)
                                   if 0 < (y == c).sum() < len(y)}
    return float(np.mean(list(per.values()))), {k: r3(v) for k, v in per.items()}

X = matriz(T); y = T.destino; COLS = list(X.columns)
rec("n_variables", X.shape[1]); rec("variables", COLS)
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=SEED, stratify=y)
rec("n_train_test", [len(Xtr), len(Xte)])
rf = nuevo_rf().fit(Xtr, ytr); Pte = rf.predict_proba(Xte); yp = rf.classes_[Pte.argmax(1)]
rec("BA", r3(balanced_accuracy_score(yte, yp))); rec("accuracy", r3((yp == yte.values).mean()))
am, per = auc_ovr(rf, Xte, yte); rec("AUC_macro", r3(am)); rec("AUC_clase", per)
pr, rc, f1, sp = precision_recall_fscore_support(yte, yp, labels=CLASES)
t6 = {c: dict(n=int(n_), P=r3(a), R=r3(b), F1=r3(f), AUC=per[c]) for c, a, b, f, n_ in zip(CLASES, pr, rc, f1, sp)}
rec("T6", t6); rec("F1_macro", r3(f1.mean()))
cm = confusion_matrix(yte, yp, labels=CLASES)
roc = {c: roc_curve((yte == c).astype(int), Pte[:, i]) for i, c in enumerate(rf.classes_)}

cv = StratifiedKFold(5, shuffle=True, random_state=SEED)
s1 = cross_val_score(nuevo_rf(), X, y, cv=cv, scoring='balanced_accuracy'); s2 = cross_val_score(nuevo_rf(), X, y, cv=cv, scoring='roc_auc_ovr')
rec("CV5_BA", [r3(s1.mean()), r3(s1.std())]); rec("CV5_AUC", [r3(s2.mean()), r3(s2.std())])

tr = (T.ani_lrt <= 2022).values
m_t = nuevo_rf().fit(X[tr], y[tr]); at, pt = auc_ovr(m_t, X[~tr], y[~tr])
rec("temporal", dict(n=[int(tr.sum()), int((~tr).sum())], AUC=r3(at), BA=r3(balanced_accuracy_score(y[~tr], m_t.predict(X[~tr]))), AUC_clase=pt))

te = T.dprtmnt.isin(['Loreto', 'Madre de Dios']).values
m_s = nuevo_rf().fit(X[~te], y[~te]); as_, ps = auc_ovr(m_s, X[te], y[te]); yps = m_s.predict(X[te])
rec("espacial", dict(n=[int((~te).sum()), int(te.sum())], AUC=r3(as_), BA=r3(balanced_accuracy_score(y[te], yps)), AUC_clase=ps,
                     F1_clase=dict(zip(CLASES, [r3(v) for v in f1_score(y[te], yps, labels=CLASES, average=None)]))))
Xnd = matriz(T, cat=['anp_categoria', 'ti_final', 'tip_lrt', 'clase_T1'])
m = nuevo_rf().fit(Xnd.loc[Xtr.index], ytr); a_nd = auc_ovr(m, Xnd.loc[Xte.index], yte)[0]
m = nuevo_rf().fit(Xnd[~te], y[~te]); a_nd_sp = auc_ovr(m, Xnd[te], y[te])[0]
rec("sin_departamento", dict(AUC_aleatorio=r3(a_nd), AUC_espacial=r3(a_nd_sp)))

# Sensibilidad: modelo con Gini (T+1) — sólo para documentar la fuga de información
Xg = matriz(T, cont=CONT + ['gini'])
m = nuevo_rf().fit(Xg.loc[Xtr.index], ytr)
rec("sensibilidad_con_gini_T1", dict(AUC=r3(auc_ovr(m, Xg.loc[Xte.index], yte)[0]), BA=r3(balanced_accuracy_score(yte, m.predict(Xg.loc[Xte.index])))))

# Umbrales por clase: elegidos con predicciones fuera de pliegue del entrenamiento, evaluados en prueba
oof = cross_val_predict(nuevo_rf(), Xtr, ytr, cv=cv, method='predict_proba')
umb = {}
grid = np.round(np.arange(0.05, 0.96, 0.01), 2)
for i, c in enumerate(rf.classes_):
    ytrb = (ytr == c).astype(int).values; yteb = (yte == c).astype(int).values
    best = grid[int(np.argmax([f1_score(ytrb, (oof[:, i] >= t).astype(int)) for t in grid]))]
    f05 = f1_score(yteb, (Pte[:, i] >= 0.5).astype(int)); fb = f1_score(yteb, (Pte[:, i] >= best).astype(int))
    umb[c] = dict(umbral=float(best), F1_05=r3(f05), F1_opt=r3(fb), dF1=r3(fb - f05))
rec("umbrales", umb)

# Clasificación en dos pasos
ybtr, ybte = ytr.isin(CONS).astype(int), yte.isin(CONS).astype(int)
m1 = nuevo_rf().fit(Xtr, ybtr); p1 = m1.predict_proba(Xte)[:, 1]
nc_tr, nc_te = ~ytr.isin(CONS), ~yte.isin(CONS)
m2 = nuevo_rf().fit(Xtr[nc_tr], ytr[nc_tr]); p2 = m2.predict(Xte[nc_te])
rec("dos_pasos", dict(P1_AUC=r3(roc_auc_score(ybte, p1)), P1_BA=r3(balanced_accuracy_score(ybte, (p1 >= 0.5).astype(int))),
                      P2_BA=r3(balanced_accuracy_score(yte[nc_te], p2)),
                      P2_F1=dict(zip(m2.classes_, [r3(v) for v in f1_score(yte[nc_te], p2, labels=m2.classes_, average=None)])),
                      P2_n=int(nc_te.sum())))

# Calibración
brier = {c: r3(brier_score_loss((yte == c).astype(int), Pte[:, i])) for i, c in enumerate(rf.classes_)}
cal_iso = CalibratedClassifierCV(nuevo_rf(), method='isotonic', cv=cv).fit(Xtr, ytr); Piso = cal_iso.predict_proba(Xte)
brier_iso = {c: r3(brier_score_loss((yte == c).astype(int), Piso[:, i])) for i, c in enumerate(cal_iso.classes_)}
rec("Brier", brier); rec("Brier_isotonico", brier_iso)
rec("AUC_macro_isotonico", r3(np.mean([roc_auc_score((yte == c).astype(int), Piso[:, i]) for i, c in enumerate(cal_iso.classes_)])))
rel = {c: calibration_curve((yte == c).astype(int), Pte[:, i], n_bins=10, strategy='quantile') for i, c in enumerate(rf.classes_)}

# Prevalencia: las probabilidades calibradas (isotónica) estiman sin sesgo la proporción de destinos;
# la predicción por argmax con class_weight='balanced' sobrerrepresenta las clases minoritarias.
rec("prevalencia_test", dict(observada=(yte.value_counts(normalize=True) * 100).round(1).to_dict(),
                             argmax_balanced=(pd.Series(yp).value_counts(normalize=True) * 100).round(1).to_dict(),
                             media_prob_calibrada=dict(zip(cal_iso.classes_, (Piso.mean(0) * 100).round(1)))))
cal_t = CalibratedClassifierCV(nuevo_rf(), method='isotonic', cv=cv).fit(X[tr], y[tr]); Pt23 = cal_t.predict_proba(X[~tr])
rec("prevalencia_temporal_2023", dict(observada=(y[~tr].value_counts(normalize=True) * 100).round(1).to_dict(),
                                      predicha_calibrada=dict(zip(cal_t.classes_, (Pt23.mean(0) * 100).round(1))),
                                      argmax_calibrado=(pd.Series(cal_t.classes_[Pt23.argmax(1)]).value_counts(normalize=True) * 100).round(1).to_dict()))

# Triaje operativo: probabilidad calibrada de consolidación P(D1+D2) por alerta
ic_ = list(cal_iso.classes_)
p_cons_te = Piso[:, ic_.index('D1_agricultura')] + Piso[:, ic_.index('D2b_mineria')]
yc_te = yte.isin(CONS).values
BINS, BLAB = [0, 0.5, 0.8, 1.0001], ['baja', 'intermedia', 'alta']
def triaje(p): return pd.cut(p, BINS, right=False, labels=BLAB)
tri = pd.DataFrame({'g': triaje(p_cons_te), 'y': yc_te})
rec("triaje_test", dict(AUC_consolidacion=r3(roc_auc_score(yc_te, p_cons_te)), Brier_consolidacion=r3(brier_score_loss(yc_te, p_cons_te)),
                        grupos={g: dict(n=int((tri.g == g).sum()), pct=round(100 * (tri.g == g).mean(), 1),
                                        cons_observada=round(100 * tri.loc[tri.g == g, 'y'].mean(), 1)) for g in BLAB}))
conf = p_cons_te

# SHAP
import shap
samp = Xte.sample(2000, random_state=SEED)
sv = shap.TreeExplainer(rf).shap_values(samp)
sv = np.stack(sv, axis=-1) if isinstance(sv, list) else sv          # (n, var, clase)
shap_clase = pd.DataFrame(np.abs(sv).mean(axis=0), index=samp.columns, columns=rf.classes_)
shap_clase['total'] = shap_clase.sum(axis=1); shap_clase = shap_clase.sort_values('total', ascending=False)
shap_clase.round(4).to_csv(OUT / "tablas/shap_importancia.csv")
rec("SHAP_top10_total", shap_clase.total.head(10).round(3).to_dict())
rec("SHAP_top5_por_clase", {c: shap_clase[c].sort_values(ascending=False).head(5).round(3).to_dict() for c in rf.classes_})
iD1 = list(rf.classes_).index('D1_agricultura')

# Moran I sobre el error binario (split aleatorio)
g = gpd.read_file(args.gpkg)[['alert_d', 'geometry']]; g['alert_d'] = g.alert_d.astype(T.alert_d.dtype)
g = g.to_crs(32718); g['x'] = g.geometry.centroid.x; g['y'] = g.geometry.centroid.y
E = T.loc[Xte.index, ['alert_d']].copy(); E['e'] = (yp != yte.values).astype(float)
E = E.merge(g[['alert_d', 'x', 'y']], on='alert_d', how='left').dropna()
nb = NearestNeighbors(n_neighbors=9).fit(E[['x', 'y']].values).kneighbors(E[['x', 'y']].values, return_distance=False)[:, 1:]
def moran(z):
    z = z - z.mean(); return float((z * z[nb].mean(1)).sum() / (z ** 2).sum())
z = E.e.values; I = moran(z); rng = np.random.default_rng(SEED)
perm = np.array([moran(rng.permutation(z)) for _ in range(999)])
rec("Moran", dict(I=r3(I), EI=float(-1 / (len(z) - 1)), p=float((1 + (perm >= I).sum()) / 1000), n=len(z), k=8))

# =====================================================================
# 7. PREDICCIÓN PROSPECTIVA 2024–2025 (clase T−1 real, sin imputación)
# =====================================================================
print("\n=== 7. PROSPECTIVO")
# modelo operativo: RF calibrado (isotónica, 5 pliegues) entrenado con las 21 870 alertas
rf_full = CalibratedClassifierCV(nuevo_rf(), method='isotonic', cv=cv).fit(X, y)
T1real = A.set_index('alert_d')[['clase_T1', 'flag_excluir']]
# ANP y distancia a vías reales para todas las alertas (salida de gee/05 y colab/02)
ANPV = pd.read_csv(D / "alertas_con_anp.csv", usecols=['alert_d', 'anp_categoria', 'dist_via_k', 'log_dist_v']).set_index('alert_d')
pros = {}; preds = []
for yr in [2024, 2025]:
    d = pd.read_csv(D / f"predicciones_{yr}.csv", low_memory=False)
    d = d.drop(columns=['clase_T1', 'flag_excluir', 'anp_categoria', 'log_dist_via', 'carretera_cerca', 'dentro_ANP_dummy',
                        'interaccion_carretera_anp'], errors='ignore')
    d = d.join(T1real, on='alert_d').join(ANPV, on='alert_d')
    d['log_dist_via'] = d.log_dist_v; d['carretera_cerca'] = (d.dist_via_k <= 2).astype(int)
    d['dentro_ANP_dummy'] = (d.anp_categoria != 'fuera_anp').astype(int); d['interaccion_carretera_anp'] = d.carretera_cerca * d.dentro_ANP_dummy
    assert d[['anp_categoria', 'log_dist_via', 'clase_T1', 'ti_final']].notna().all().all()
    n0 = len(d); d = d[d.flag_excluir == 0].copy()
    Pp = rf_full.predict_proba(matriz(d, cols=COLS))
    for i, c in enumerate(rf_full.classes_): d[f'p_{c}'] = Pp[:, i]
    d['p_consolidacion'] = d.p_D1_agricultura + d.p_D2b_mineria; d['p_recuperacion'] = d.p_D4_regeneracion + d.p_D5_bosque
    d['triaje'] = triaje(d.p_consolidacion.values).astype(str)
    pros[yr] = dict(n_total=n0, n_excl_T1=n0 - len(d), n=len(d),
                    prevalencia_esperada=dict(zip(rf_full.classes_, (Pp.mean(0) * 100).round(1))),
                    triaje={g: dict(n=int((d.triaje == g).sum()), pct=round(100 * (d.triaje == g).mean(), 1)) for g in BLAB},
                    p_cons_media=r3(d.p_consolidacion.mean()))
    preds.append(d[['alert_d', 'ani_lrt', 'dprtmnt', 'p_consolidacion', 'p_recuperacion', 'triaje'] + [f'p_{c}' for c in rf_full.classes_]])
rec("prospectivo", pros)
pd.concat(preds).to_csv(OUT / "tablas/predicciones_2024_2025.csv", index=False)

# =====================================================================
# 8. SERNANP (Sección 3.4)
# =====================================================================
print("\n=== 8. SERNANP")
sa = S[S.CONFIABILIDAD == 'ALTO']
rec("SN_n", len(sa)); rec("SN_n_total", len(S))
zon = sa.groupby('ZONIFI_ANP').AREA_DEFO.agg(['sum', 'count', 'mean']).round(2).sort_values('sum', ascending=False)
zon.to_csv(OUT / "tablas/sernanp_zonificacion.csv"); rec("SN_zonas", zon.to_dict('index'))
cat = sa.pivot_table(index='CATEGORIA', columns='ANIO_REPORTE', values='AREA_DEFO', aggfunc='sum').round(0)
cat.to_csv(OUT / "tablas/sernanp_categoria_anio.csv"); rec("SN_categoria_anio", cat.fillna(0).to_dict('index'))
m = sa[sa.DEFO_CAUSA == 'MINERIA']
rec("SN_mineria", dict(n=len(m), area=round(m.AREA_DEFO.sum(), 2), anps=m.ANP.unique().tolist(),
                        por_anio=m.groupby('ANIO_REPORTE').AREA_DEFO.sum().round(2).to_dict(),
                        por_zona=m.groupby('ZONIFI_ANP').AREA_DEFO.sum().round(2).to_dict(),
                        por_bosque=m.groupby('TIPO_BOSQUE').AREA_DEFO.sum().round(2).to_dict()))
mm = m.groupby(['ANIO_REPORTE', 'MES_IMAG']).AREA_DEFO.agg(['sum', 'count'])
pk = mm['sum'].idxmax(); rec("SN_mineria_pico", dict(anio=int(pk[0]), mes=int(pk[1]), area=round(mm.loc[pk, 'sum'], 2), n=int(mm.loc[pk, 'count'])))
ag = sa[sa.DEFO_CAUSA == 'AGRICULTURA']
rec("SN_agri_pct_secundario", round(100 * ag.loc[ag.TIPO_BOSQUE == 'SECUNDARIO', 'AREA_DEFO'].sum() / ag.AREA_DEFO.sum(), 1))

# =====================================================================
json.dump(R, open(OUT / "resultados.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
pickle.dump(dict(cm=cm, roc=roc, rel=rel, auc=per, shap_sv=sv[:, :, iD1], shap_X=samp, shap_clase=shap_clase,
                 conf=conf, evo=evo, R21=R21[['trayectoria', 'tray3', 'anp_categoria', 'ti_final']], t5=t5,
                 ti=R["TI"], pros=pros, dep=dep, clases=list(rf.classes_)), open(OUT / "modelo_salidas.pkl", "wb"))
print("\nOK — resultados en", OUT)
