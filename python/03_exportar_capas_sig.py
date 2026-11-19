"""Exporta las capas SIG (shapefile, EPSG:4326) para elaborar los mapas del artículo en ArcGIS Pro / QGIS.
Uso: python 03_exportar_capas_sig.py --datos <carpeta_csv> --gpkg <alertas_con_distancia.gpkg> --limites <gadm41_PER_1.json>
                                     --resultados <carpeta de 01_resultados.py> --salida <carpeta>
"""
import argparse
from pathlib import Path
import pandas as pd, geopandas as gpd

ap = argparse.ArgumentParser()
for a in ["datos", "gpkg", "limites", "resultados", "salida"]: ap.add_argument(f"--{a}", required=True)
a = ap.parse_args(); D, RES, OUT = Path(a.datos), Path(a.resultados), Path(a.salida); OUT.mkdir(parents=True, exist_ok=True)

COD = {'D1_agricultura': 'D1', 'D2b_mineria': 'D2', 'D3_suelo_expuesto': 'D3', 'D4_regeneracion': 'D4', 'D5_bosque': 'D5', 'otros': 'OT'}
NOM = {'D1': 'Agricultura', 'D2': 'Minería', 'D3': 'Suelo expuesto', 'D4': 'Regeneración', 'D5': 'Bosque', 'OT': 'Otras clases'}
CONS = {'D1', 'D2'}; REC = {'D4', 'D5'}

G = gpd.read_file(a.gpkg)[['alert_d', 'geometry']]; G['alert_d'] = G.alert_d.astype('int64')
A = pd.read_csv(D / "alertas_con_trayectoria.csv"); T = pd.read_csv(D / "tabla_maestra_final.csv")
ANP = pd.read_csv(D / "alertas_con_anp.csv", usecols=['alert_d', 'anp_categoria', 'dprtmnt', 'tip_lrt', 'dist_via_k'])
T2 = pd.read_csv(D / "alertas_2021_T2_T3.csv"); PR = pd.read_csv(RES / "tablas/predicciones_2024_2025.csv")
for df in (A, T, ANP, T2, PR): df['alert_d'] = df.alert_d.astype('int64')

def guardar(gdf, nombre, puntos=True):
    gdf = gdf.set_crs(4326) if gdf.crs is None else gdf.to_crs(4326)
    gdf.to_file(OUT / f"{nombre}.shp", encoding="utf-8")
    if puntos:
        p = gdf.copy(); p['geometry'] = gdf.to_crs(32718).geometry.representative_point().to_crs(4326)
        p.to_file(OUT / f"{nombre}_pts.shp", encoding="utf-8")
    print(nombre, len(gdf))

# 1. Todas las alertas con su estado en el embudo de filtrado
s = A.merge(ANP, on='alert_d', how='left')
s['estado'] = 'analitico'
s.loc[s.ani_lrt >= 2024, 'estado'] = 'sin_T1_2024_25'
s.loc[(s.ani_lrt <= 2023) & (s.flag_excluir == 1), 'estado'] = 'excl_T1_no_nat'
s.loc[(s.ani_lrt <= 2023) & (s.flag_excluir == 0) & (s.flag_mixta == 1), 'estado'] = 'excl_mixto'
s.loc[(s.ani_lrt <= 2023) & (s.estado == 'analitico') & (s.destino == 'otros'), 'estado'] = 'excl_otros'
assert (s.estado == 'analitico').sum() == len(T)
todas = G.merge(s, on='alert_d')
todas = todas.assign(anio=todas.ani_lrt.astype(int), area_ha=todas.area_ha.round(3), dpto=todas.dprtmnt, tipo=todas.tip_lrt,
                     anp_cat=todas.anp_categoria, dist_km=todas.dist_via_k.round(3), clase_T1=todas.clase_T1)
guardar(todas[['alert_d', 'anio', 'area_ha', 'dpto', 'tipo', 'anp_cat', 'dist_km', 'clase_T1', 'estado', 'geometry']], "01_alertas_todas_2021_2025")

# 2. Conjunto analítico 2021–2023 con destino T+1
t = G.merge(T, on='alert_d')
t['dest'] = t.destino.map(COD); t['dest_nom'] = t.dest.map(NOM)
t['consol'] = t.dest.isin(CONS).astype(int); t['recup'] = t.dest.isin(REC).astype(int)
t = t.assign(anio=t.ani_lrt.astype(int), area_ha=t.area_ha.round(3), dpto=t.dprtmnt, tipo=t.tip_lrt, anp_cat=t.anp_categoria,
             ti_cat=t.ti_final, dist_km=t.dist_via_km.round(3))
guardar(t[['alert_d', 'anio', 'area_ha', 'dpto', 'tipo', 'anp_cat', 'ti_cat', 'dist_km', 'clase_T1', 'dest', 'dest_nom', 'consol',
           'recup', 'geometry']], "02_alertas_2021_2023_destino_T1")

# 3. Trayectorias 2021 (T+1, T+2, T+3)
def cl(x): return 'C' if x in CONS else 'R' if x in REC else 'S' if x == 'D3' else 'O'
def tray(r):
    a1, a2, a3 = cl(r.d_T1), cl(r.d_T2), cl(r.d_T3)
    if a1 == 'C' and a2 == 'C': return 'Consolidación rápida'
    if a1 == 'S' and a2 == 'C': return 'Consolidación progresiva'
    if a1 == 'S' and a2 == 'S' and a3 == 'C': return 'Consolidación tardía'
    if a1 == 'R' and a2 == 'R': return 'Recuperación sostenida'
    if a1 == 'S' and a2 == 'R': return 'Recuperación post-tránsito'
    if a1 == 'C' and a2 == 'R': return 'Reversión post-uso'
    return 'Trayectoria inestable'
r = T2[T2.alert_d.isin(T.alert_d)].copy()
r['d_T1'] = r.destino.map(COD); r['d_T2'] = r.destino_T2.map(COD); r['d_T3'] = r.destino_T3.map(COD)
r['tray'] = r.apply(tray, axis=1)
r = G.merge(r, on='alert_d').merge(T[['alert_d', 'anp_categoria', 'ti_final']], on='alert_d')
r = r.assign(area_ha=r.area_ha.round(3), dpto=r.dprtmnt, anp_cat=r.anp_categoria, ti_cat=r.ti_final)
guardar(r[['alert_d', 'area_ha', 'dpto', 'anp_cat', 'ti_cat', 'd_T1', 'd_T2', 'd_T3', 'tray', 'geometry']], "03_trayectorias_alertas_2021")

# 4. Predicciones 2024–2025 (probabilidades calibradas y triaje)
p = G.merge(PR, on='alert_d')
p = p.rename(columns={'p_D1_agricultura': 'p_D1', 'p_D2b_mineria': 'p_D2', 'p_D3_suelo_expuesto': 'p_D3', 'p_D4_regeneracion': 'p_D4',
                      'p_D5_bosque': 'p_D5', 'p_consolidacion': 'p_consol', 'p_recuperacion': 'p_recup'})
for c in ['p_D1', 'p_D2', 'p_D3', 'p_D4', 'p_D5', 'p_consol', 'p_recup']: p[c] = p[c].round(4)
p = p.assign(anio=p.ani_lrt.astype(int), dpto=p.dprtmnt)
guardar(p[['alert_d', 'anio', 'dpto', 'p_D1', 'p_D2', 'p_D3', 'p_D4', 'p_D5', 'p_consol', 'p_recup', 'triaje', 'geometry']],
        "04_prediccion_2024_2025_triaje")

# 5. Departamentos (GADM 4.1)
L = gpd.read_file(a.limites)
fix = {"MadredeDios": "Madre de Dios", "SanMartín": "San Martín", "LaLibertad": "La Libertad", "LimaProvince": "Lima Provincia"}
L['dpto'] = L.NAME_1.replace(fix)
dep = pd.read_csv(RES / "tablas/departamentos.csv", index_col=0)
L = L.merge(dep[['n', 'D1_agricultura', 'D2b_mineria', 'D5_bosque', 'consolidacion']].rename(
    columns={'n': 'n_alertas', 'D1_agricultura': 'pct_D1', 'D2b_mineria': 'pct_D2', 'D5_bosque': 'pct_D5', 'consolidacion': 'pct_consol'}),
    left_on='dpto', right_index=True, how='left')
guardar(L[['dpto', 'n_alertas', 'pct_D1', 'pct_D2', 'pct_D5', 'pct_consol', 'geometry']], "05_departamentos_GADM", puntos=False)
print("OK", OUT)
