"""English version of the figures (same code as 02_figuras.py; only labels are translated). Output: <resultados>/figures_en/
Usage: python 02_figuras_en.py --datos ... --gpkg ... --limites ... --resultados ...
"""
from pathlib import Path
src = (Path(__file__).with_name("02_figuras.py")).read_text(encoding="utf-8")
TR = [
    ('FIG = RES / "figuras"', 'FIG = RES / "figures_en"'),
    ('"D1 Agricultura", "D2 Minería", "D3 Suelo expuesto", "D4 Regeneración", "D5 Bosque"',
     '"D1 Agriculture", "D2 Mining", "D3 Bare soil", "D4 Regeneration", "D5 Forest"'),
    ('label="Alertas 2024–2025 (sin T+1)"', 'label="2024–2025 alerts (no T+1)"'),
    ('title="Alertas 2021–2023 (n = 21 870)"', 'title="2021–2023 alerts (n = 21,870)"'),
    ('"Conjunto analítico"', '"Analytical dataset"'), ('"Excluidas / sin T+1"', '"Excluded / no T+1"'),
    ('"(a) Alertas verificadas por año"', '"(a) Verified alerts per year"'), ('"N.º de alertas"', '"Number of alerts"'),
    ('"(b) Alertas por departamento (2021–2025)"', '"(b) Alerts per department (2021–2025)"'),
    ('"% de alertas (T+1)"', '"% of alerts (T+1)"'),
    ("'dentro_intangible': 'ANP intangible', 'dentro_uso_directo': 'ANP uso directo'", "'dentro_intangible': 'PA strict protection', 'dentro_uso_directo': 'PA direct use'"),
    ("'buffer_10km': 'Buffer 5–10 km', 'fuera_anp': 'Fuera de ANP'", "'buffer_10km': 'Buffer 5–10 km', 'fuera_anp': 'Outside PA'"),
    ('"(a) Categoría de ANP"', '"(a) Protected area category"'),
    ("'ti_titulada': 'TI titulada', 'ti_en_proceso': 'TI en proceso', 'fuera_ti': 'Fuera de TI'",
     "'ti_titulada': 'Titled IT', 'ti_en_proceso': 'IT in titling', 'fuera_ti': 'Outside IT'"),
    ('"(b) Territorio indígena"', '"(b) Indigenous territory"'),
    ('"% de alertas (IC 95 % Wilson)"', '"% of alerts (95% Wilson CI)"'),
    ('label="Consolidación (D1 + D2)"', 'label="Consolidation (D1 + D2)"'),
    ('label="Recuperación / IESA (D4 + D5)"', 'label="Recovery / PASI (D4 + D5)"'),
    ('zn.index = [z.replace("ZONA DE ", "").replace("ZONA ", "").capitalize() for z in zn.index]', 'zn.index = [ZEN.get(z, z) for z in zn.index]'),
    ('"(a) Área deforestada total (ha)"', '"(a) Total deforested area (ha)"'), ('"(b) Intensidad media (ha/evento)"', '"(b) Mean intensity (ha/event)"'),
    ('ax.text(2023.08, pos[c], c.capitalize()', 'ax.text(2023.08, pos[c], CEN.get(c, c)'), ('"Área deforestada (ha)"', '"Deforested area (ha)"'),
    ('"(a) Área mensual deforestada por minería (ha) — anual: "', '"(a) Monthly area deforested by mining (ha) — annual: "'),
    ('z.index = [s.replace("ZONA DE ", "").capitalize() for s in z.index]', 'z.index = [ZEN.get(s, s) for s in z.index]'),
    ('"(b) Por zonificación interna"', '"(b) By internal zoning"'),
    ('["Bosque " + s.lower() for s in b.index]', '[{"PRIMARIO": "Primary forest", "SECUNDARIO": "Secondary forest"}[s] for s in b.index]'),
    ('"(c) Por tipo de bosque afectado"', '"(c) By forest type affected"'),
    ('"Tasa de falsos positivos"', '"False positive rate"'), ('"Tasa de verdaderos positivos"', '"True positive rate"'),
    ('"Clase predicha"', '"Predicted class"'), ('"Clase observada"', '"Observed class"'), ('"% de la clase observada"', '"% of observed class"'),
    ('ax.set_xlabel("Probabilidad predicha media"); ax.set_ylabel("Frecuencia observada")', 'ax.set_xlabel("Mean predicted probability"); ax.set_ylabel("Observed frequency")'),
    ('replace("tip_lrt_", "Presión: ").replace("dprtmnt_", "Dpto: ").replace("anp_categoria_", "ANP: ").replace("ti_final_", "TI: ")',
     'replace("tip_lrt_", "Pressure: ").replace("dprtmnt_", "Dept: ").replace("anp_categoria_", "PA: ").replace("ti_final_", "IT: ")'),
    ('.replace("clase_T1_", "T−1: ").replace("log_are", "log(área)").replace("log_dist_via", "log(dist. vía)").replace("ani_lrt", "Año de alerta")',
     '.replace("clase_T1_", "T−1: ").replace("bosque_primario", "forest").replace("formacion_natural", "natural formation").replace("log_are", "log(area)").replace("log_dist_via", "log(road distance)").replace("ani_lrt", "Alert year")'),
    ('.replace("carretera_cerca", "Vía ≤ 2 km").replace("ilegal_mining", "minería ilegal").replace("agriculture", "agricultura"))',
     '.replace("carretera_cerca", "Road ≤ 2 km").replace("ilegal_mining", "illegal mining"))'),
    ('"Media |SHAP| (suma sobre clases)"', '"Mean |SHAP| (sum over classes)"'), ('"(a) Importancia global"', '"(a) Global importance"'),
    ('"Valor SHAP para D1 Agricultura"', '"SHAP value for D1 Agriculture"'), ('"(b) Efecto sobre P(D1)"', '"(b) Effect on P(D1)"'),
    ('set_yticklabels(["bajo", "alto"])', 'set_yticklabels(["low", "high"])'),
    ('LAB.get(c, "Otras clases")', 'LAB.get(c, "Other classes")'),
    ('f"% de alertas 2021 (n = {R[\'n_2021_analitico\']:,})".replace(",", " ")', 'f"% of 2021 alerts (n = {R[\'n_2021_analitico\']:,})"'),
    ('label=t); left += v', 'label=TEN[t]); left += v'),
    ('a.set_xlabel("% de alertas 2021")', 'a.set_xlabel("% of 2021 alerts")'),
    ('"(a) Observado 2021–2023 y esperado 2024–2025*"', '"(a) Observed 2021–2023 and expected 2024–2025*"'),
    ('a1.set_xlabel("% de alertas")', 'a1.set_xlabel("% of alerts")'),
    ('"Alta (P ≥ 0,8)"', '"High (P ≥ 0.8)"'), ('"Intermedia (0,5–0,8)"', '"Intermediate (0.5–0.8)"'), ('"Baja (P < 0,5)"', '"Low (P < 0.5)"'),
    ('"(b) Probabilidad calibrada de consolidación, 2024–2025"', '"(b) Calibrated probability of consolidation, 2024–2025"'),
    ('" {v:.2f} ha ({100*v/z.sum():.1f} %)"', '" {v:.2f} ha ({100*v/z.sum():.1f}%)"'),
    ('" {v:.2f} ha ({100*v/b.sum():.1f} %)"', '" {v:.2f} ha ({100*v/b.sum():.1f}%)"'),
]
HEADER = '''
ZEN = {"ZONA DE APROVECHAMIENTO DIRECTO": "Direct use", "ZONA DE USO ESPECIAL": "Special use", "ZONA SILVESTRE": "Wilderness",
       "NO ZONIFICADO": "Not zoned", "ZONA DE RECUPERACION": "Recovery", "ZONA DE PROTECCION ESTRICTA": "Strict protection",
       "ZONA DE USO TURISTICO Y RECREATIVO": "Tourism and recreation", "ZONA HISTORICO CULTURA": "Historical-cultural"}
CEN = {"RESERVA COMUNAL": "Communal reserve", "BOSQUE DE PROTECCIÓN": "Protection forest", "RESERVA NACIONAL": "National reserve",
       "PARQUE NACIONAL": "National park", "ZONAS RESERVADAS": "Reserved zone"}
TEN = {"Consolidación rápida": "Rapid consolidation", "Recuperación sostenida": "Sustained recovery", "Otras": "Other"}
'''
for a, b in TR:
    assert a in src, f"not found: {a[:70]}"
    src = src.replace(a, b)
src = src.replace("warnings.filterwarnings(\"ignore\")", "warnings.filterwarnings(\"ignore\")" + HEADER, 1)
exec(compile(src, "02_figuras_en", "exec"))
