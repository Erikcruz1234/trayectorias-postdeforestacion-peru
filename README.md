# Trayectorias post-deforestación en la Amazonía peruana (2021–2025)

**Autor:** Erik Gianmarco Cruz Cruz  
**Afiliación:** Escuela Profesional de Ingeniería Ambiental, Universidad Nacional Mayor de San Marcos, Lima, Perú  
**Contacto:** erikgian15@gmail.com  
**Licencia:** [CC BY-NC 4.0](LICENSE)

---

## Descripción

Este repositorio contiene el código completo que respalda el artículo:

> Cruz Cruz, E.G. (2026). *Trayectorias post-deforestación en la Amazonía peruana (2021–2025): análisis de destinos de cobertura, trayectorias dinámicas y predicción prospectiva mediante Random Forest, interpretabilidad SHAP y grupo control de pseudo-alertas basado en datos de MapBiomas.*

El estudio analiza **39 649 alertas verificadas de MapBiomas Alerta Perú (2021–2025)** y clasifica su destino post-deforestación en cinco categorías: consolidación agrícola (D1), minería (D2), suelo expuesto (D3), regeneración incipiente (D4) y bosque mantenido (D5). La reproducibilidad completa está garantizada mediante semilla fija (`seed = 42`) en todos los análisis estocásticos.

---

## Estructura del repositorio

```
trayectorias-postdeforestacion-peru/
│
├── README.md
├── LICENSE                          ← CC BY-NC 4.0
│
├── gee/                             ← Scripts de Google Earth Engine (JavaScript)
│   ├── 01_alertas_con_trayectoria.js    ← Pipeline principal T−1 / T+1 / Gini
│   ├── 03_trayectorias_T2_T3.js         ← Seguimiento T+2 y T+3 (alertas 2021)
│   ├── 04_pseudo_alertas_control.js     ← Grupo control (n=1 273 pseudo-alertas)
│   └── 05_clasificacion_anp_ti.js       ← Categoría ANP y TI por alerta
│
├── r/
│   └── 01_preprocesamiento_alertas.R    ← Limpieza del shapefile, filtros, exports
│
└── colab/                           ← Notebooks de Google Colab (Python)
    ├── 02_distancia_vias_osm.ipynb      ← Cálculo de distancias con OSM + MTC
    ├── 03_random_forest_shap_trayectorias.ipynb  ← Modelo RF, SHAP, trayectorias
    ├── 04_analisis_sernanp.ipynb        ← Análisis intra-ANP con datos SERNANP
    └── 05_figuras_articulo.ipynb        ← Generación de todas las figuras del artículo
```

---

## Pipeline de datos — embudo de filtrado

| Paso | Descripción | N | % del total |
|------|-------------|---|-------------|
| 0 | Alertas brutas descargadas (2021–2025, ≥ 0.5 ha) | 39 649 | 100 % |
| 1 | Reservadas: 2024–2025 (sin T+1 en Colección 3.0) | 17 779 | 44.8 % |
| 2 | Excluidas: T−1 no forestal (class_T1 = 'otros') | 4 152 | 10.5 % |
| 3 | Excluidas: sin T+1 disponible (flag_sin_T1p) | 0 | 0.0 % |
| **4** | **Conjunto analítico final (2021–2023)** | **21 870** | **55.2 %** |

**Grupo control:** 1 273 pseudo-alertas obtenidas de 2 000 solicitadas (tasa de rechazo: 36.4 %). Semilla = 42.

---

## Fuentes de datos

| Fuente | Descripción | Acceso |
|--------|-------------|--------|
| MapBiomas Alerta Perú | 39 649 alertas verificadas 2021–2025 | [plataforma.peru.alerta.mapbiomas.org](https://plataforma.peru.alerta.mapbiomas.org) |
| MapBiomas Perú Colección 3.0 | Clasificación anual 30 m (1985–2024) | GEE: `projects/mapbiomas-public/assets/peru/collection3/...` |
| SERNANP (2024) | Shapefile ANP del SINANPE | [sernanp.gob.pe](https://www.sernanp.gob.pe) |
| SERNANP (2024b) | Dataset monitoreo deforestación intra-ANP | [datosabiertos.gob.pe](https://www.datosabiertos.gob.pe/dataset/registro-de-monitoreo-de-la-deforestación-en-el-ámbito-de-las-áreas-naturales-protegidas) |
| IBC (2024) | Territorios indígenas (SICNA) | [ibcperu.org](https://ibcperu.org) |
| MTC + OSM (2024) | Red vial nacional + trochas | [datosabiertos.gob.pe](https://www.datosabiertos.gob.pe/dataset/red-vial-nacional-del-sistema-nacional-de-carreteras-2022-2024-ministerio-de-transportes-y) |
| USGS SRTM 30 m | Topografía | GEE: `USGS/SRTMGL1_003` |

---

## Descripción de scripts

### GEE (Google Earth Engine)

**`gee/01_alertas_con_trayectoria.js`**  
Script principal del pipeline. Para cada alerta extrae:
- `clase_T1`: cobertura del año previo a la alerta (T−1) → determina si es deforestación real sobre bosque
- `destino`: clase de cobertura modal en T+1 (año siguiente) → destino post-deforestación (D1–D5)
- `gini`: índice de heterogeneidad interna del polígono en T+1 (Gini = 1 − Σpᵢ²)
- Flags de calidad: `flag_excluir`, `flag_mixta`, `flag_sin_T1p`

**`gee/02_distancia_vias.js`** *(ver notebook Colab `02_distancia_vias_osm.ipynb`)*  
Calcula la distancia euclidiana mínima de cada centroide de alerta a la red vial (MTC + OSM). Genera `log_dist_via`.

**`gee/03_trayectorias_T2_T3.js`**  
Extiende el seguimiento a T+2 (2023) y T+3 (2024) para alertas de 2021 únicamente. Permite construir las 7 trayectorias dinámicas.

**`gee/04_pseudo_alertas_control.js`**  
Genera el grupo control: 1 273 puntos en bosque primario o formación natural (2020) sin alerta verificada 2021–2023. Extrae destino en T+1, T+2 y T+3. Calibra el IESA de referencia (99.0 % en T+1).

**`gee/05_clasificacion_anp_ti.js`**  
Clasifica cada alerta en 5 categorías ANP (intangible, uso directo, buffer 5 km, buffer 10 km, fuera de ANP) y 3 categorías TI (titulada, en proceso, fuera de TI).

### R

**`r/01_preprocesamiento_alertas.R`**  
Carga el shapefile de alertas, aplica filtros de calidad (área ≥ 0.5 ha, corrección de geometrías), crea variables derivadas (log_area, tipo_macro), genera subsets para el modelo y ejecuta el test Kruskal-Wallis de variación de área entre años.

### Colab (Python)

**`colab/02_distancia_vias_osm.ipynb`**  
Combina la red vial del MTC con datos de OpenStreetMap. Calcula distancias y genera `dist_via_km` y `log_dist_via` para cada alerta.

**`colab/03_random_forest_shap_trayectorias.ipynb`**  
Notebook principal del modelado:
- Construcción de la tabla maestra con 36 variables
- Entrenamiento Random Forest (n_estimators=300, class_weight='balanced', min_samples_leaf=5)
- Validación: split aleatorio 70/30, CV 5-fold, prospectiva temporal (2021+2022→2023), split espacial (Loreto+Madre de Dios)
- Experimento de ablación (sin gini ni clase_T1)
- Optimización de umbrales por clase (maximizando F1)
- Clasificación en dos pasos (consolidación vs. no consolidación)
- Calibración probabilística (Brier Score, reliability diagram)
- Valores SHAP (importancia global + beeswarm plot por clase)
- Análisis de trayectorias dinámicas (7 categorías, n=7 768)
- Predicciones prospectivas 2024–2025 con cuantificación de incertidumbre

**`colab/04_analisis_sernanp.ipynb`**  
Análisis del dataset SERNANP de deforestación intra-ANP (n=4 877 eventos, alta confiabilidad):
- Gradiente de deforestación por zonificación interna
- Tendencia temporal 2021–2023 por categoría de ANP
- Caso específico: escalada de minería ilegal en Reserva Nacional Tambopata

**`colab/05_figuras_articulo.ipynb`**  
Genera todas las figuras publicadas en el artículo en resolución 300 dpi (PNG) y vectorial (SVG/PDF).

---

## Cómo reproducir el análisis

**Paso 1 — Descargar los datos**
```
1. MapBiomas Alerta Perú: https://plataforma.peru.alerta.mapbiomas.org
   → Descargar shapefile de alertas 2021–2025 (área ≥ 0.5 ha)
2. SERNANP intra-ANP: https://www.datosabiertos.gob.pe/...
   → Dataset_DeforestacionAnp_SERNANP.csv
3. IBC territorios indígenas: https://ibcperu.org
4. MTC red vial: https://www.datosabiertos.gob.pe/...
```

**Paso 2 — Preprocesamiento en R**
```r
source("r/01_preprocesamiento_alertas.R")
# Salidas en data/clean/
```

**Paso 3 — Pipeline GEE** (ejecutar en orden en code.earthengine.google.com)
```
01_alertas_con_trayectoria.js  → alertas_con_trayectoria.csv
02_distancia_vias.js           → alertas_con_distancia.csv
03_trayectorias_T2_T3.js       → alertas_2021_T2_T3.csv
04_pseudo_alertas_control.js   → pseudo_alertas_control.csv
05_clasificacion_anp_ti.js     → alertas_con_anp_ti.csv
```

**Paso 4 — Modelo y análisis en Google Colab**
```
colab/03_random_forest_shap_trayectorias.ipynb
colab/04_analisis_sernanp.ipynb
colab/05_figuras_articulo.ipynb
```

> **Nota:** Todos los notebooks asumen que los CSV están en `Google Drive > Proyecto_MapBiomas/`. Ajustar la variable `RUTA` si la estructura de carpetas es diferente.

---

## Resultados principales

| Indicador | Valor |
|-----------|-------|
| Alertas analizadas (2021–2023) | 21 870 |
| Consolidación agrícola (D1) en T+1 | 72.5 % |
| IESA alertas reales (T+1) | 20.8 % |
| IESA grupo control (T+1) | 99.0 % |
| Diferencia IESA (Δ) | −78.3 pp (p < 0.001) |
| Consolidación rápida (trayectoria 3 años) | 75.1 % |
| AUC macro (split aleatorio) | 0.887 |
| AUC macro (validación espacial) | 0.746 |
| AUC macro (validación temporal) | 0.825 |
| AUC efectivo con imputación (2024–2025) | 0.823 |

---

## Citar este trabajo

```bibtex
@article{cruzcruz2026trayectorias,
  title   = {Trayectorias post-deforestaci{\'o}n en la Amazon{\'\i}a peruana
             (2021--2025): an{\'a}lisis de destinos de cobertura, trayectorias
             din{\'a}micas y predicci{\'o}n prospectiva mediante Random Forest,
             interpretabilidad SHAP y grupo control de pseudo-alertas basado
             en datos de MapBiomas},
  author  = {Cruz Cruz, Erik Gianmarco},
  year    = {2026},
  institution = {Universidad Nacional Mayor de San Marcos},
  address = {Lima, Per{\'u}},
  url     = {https://github.com/erikgiancruz/trayectorias-postdeforestacion-peru}
}
```

---

*Este repositorio fue creado como parte del Premio MapBiomas Perú — 3ra Edición, Categoría Joven (2026).*
