# Trayectorias post-deforestación en la Amazonía peruana (2021–2025)

**Autor:** Erik Gianmarco Cruz Cruz — Escuela Profesional de Ingeniería Ambiental, Universidad Nacional Mayor de San Marcos, Lima, Perú
**Contacto:** erikgian15@gmail.com · **Licencia:** [CC BY-NC 4.0](LICENSE)

Código que reproduce **todos** los valores, tablas y figuras del artículo:

> Cruz Cruz, E. G. *Trayectorias post-deforestación en la Amazonía peruana (2021–2025): destinos de cobertura, trayectorias plurianuales y predicción con Random Forest a partir de alertas verificadas de MapBiomas.* (manuscrito enviado).

Una versión preliminar de este trabajo resultó ganadora del Premio MapBiomas Perú, 3.ª edición, categoría Joven (2026).

---

## Estructura

```
gee/                                   Google Earth Engine (JavaScript): extracción de cobertura
  01_alertas_con_trayectoria.js        clase T−1, destino modal T+1, Gini–Simpson T+1, flags  → alertas_con_trayectoria.csv
  03_trayectorias_T2_T3.js             destinos T+2 y T+3 de las alertas 2021               → alertas_2021_T2_T3.csv
  04_pseudo_alertas_control.js         grupo control (1 273 pseudo-alertas, semilla 42)     → pseudo_alertas_control.csv
  05_clasificacion_anp_ti.js           categoría ANP y TI de cada alerta                     → alertas_con_anp.csv
r/
  01_preprocesamiento_alertas.R        limpieza del shapefile de alertas, área ≥ 0,5 ha, variables derivadas
colab/
  02_distancia_vias_osm.ipynb          distancia a la red vial (MTC + OpenStreetMap)          → alertas_con_distancia.gpkg
python/
  01_resultados.py                     TODOS los análisis del artículo                       → resultados.json, tablas/
  02_figuras.py                        las 14 figuras del artículo (PNG, 300 dpi)            → figuras/
  02_figuras_en.py                     las mismas figuras con etiquetas en inglés            → figures_en/
  03_exportar_capas_sig.py             capas shapefile para mapas en ArcGIS Pro / QGIS        → capas/
requirements.txt                       versiones exactas usadas
```

## Reproducir el análisis

1. Ejecutar los scripts de `gee/`, `r/` y `colab/02` (o descargar los archivos intermedios; ver *Datos*).
2. Instalar el entorno: `pip install -r requirements.txt` (Python 3.13).
3. Ejecutar:

```bash
python python/01_resultados.py --datos <carpeta_csv> --gpkg <alertas_con_distancia.gpkg> --salida resultados
python python/02_figuras.py   --datos <carpeta_csv> --gpkg <alertas_con_distancia.gpkg> \
                              --limites gadm41_PER_1.json --resultados resultados
```

Opcional:

```bash
python python/02_figuras_en.py --datos <carpeta_csv> --gpkg <alertas_con_distancia.gpkg> --limites gadm41_PER_1.json --resultados resultados
python python/03_exportar_capas_sig.py --datos <carpeta_csv> --gpkg <alertas_con_distancia.gpkg> --limites gadm41_PER_1.json                                        --resultados resultados --salida capas
```

Todos los procedimientos estocásticos usan `random_state = 42`. `01_resultados.py` escribe cada valor citado en el artículo en `resultados/resultados.json`.

### Archivos de entrada (`--datos`)

| Archivo | Contenido |
|---|---|
| `alertas_con_trayectoria.csv` | 39 649 alertas: clase T−1, destino T+1, Gini–Simpson T+1, flags de calidad |
| `tabla_maestra_final.csv` | conjunto analítico 2021–2023 (21 870) con ANP, TI y vías |
| `alertas_2021_T2_T3.csv` | destinos T+2 y T+3 de las alertas 2021 |
| `pseudo_alertas_control.csv` | grupo control |
| `alertas_con_anp.csv` | categoría ANP y distancia a vías de las 39 649 alertas |
| `predicciones_2024.csv`, `predicciones_2025.csv` | variables de las alertas 2024–2025 (área, tipo, TI, departamento) |
| `Dataset_DeforestacionAnp_SERNANP.csv` | registro de deforestación en ANP (SERNANP, 2024b) |

Límites departamentales: GADM v4.1 (`gadm41_PER_1.json`, https://gadm.org).

## Decisiones metodológicas clave

* **Conjunto analítico (21 870 alertas 2021–2023).** De 26 022 alertas con T+1 disponible se excluyen: 1 010 con cobertura T−1 no natural, 3 073 polígonos mixtos en T+1 (Gini–Simpson > 0,5; la moda no representa el destino) y 69 con clase T+1 fuera de los cinco destinos. Se reporta un análisis de sensibilidad incluyendo los polígonos mixtos.
* **Sin fuga de información.** El índice de Gini–Simpson se calcula en T+1 (mismo mapa que el destino); se usa solo como filtro de calidad de la etiqueta y **no** como predictor. El modelo usa 34 variables medidas antes o en el momento de la alerta. El modelo con Gini se reporta solo como sensibilidad.
* **Validación** aleatoria, cruzada (5 pliegues), temporal (2021–2022 → 2023) y espacial (→ Loreto + Madre de Dios); umbrales elegidos con predicciones fuera de pliegue del entrenamiento.
* **Predicción 2024–2025** con variables reales (cobertura T−1, ANP, distancia a vías); distribución esperada = media de probabilidades calibradas (isotónica), no recuento de clases asignadas.

## Resultados principales

| Indicador | Valor |
|---|---|
| Alertas verificadas / conjunto analítico | 39 649 / 21 870 |
| Consolidación en T+1 (D1 agricultura + D2 minería) | 75,3 % (D1: 72,5 %) |
| IESA alertas 2021 vs. grupo control (T+1) | 21,7 % vs. 98,0 % (Δ = −76,3 pp; χ² = 2 789,7; p < 0,001) |
| Consolidación en zonas intangibles vs. fuera de ANP | 28,6 % (n = 21) vs. 76,5 % |
| OR ajustado de consolidación, ANP o zona de influencia ≤ 10 km | 0,82 |
| Consolidación rápida (alertas 2021, tres años) | 75,8 % |
| AUC macro: aleatorio / temporal / espacial | 0,863 / 0,783 / 0,695 |
| AUC con Gini de T+1 (fuga, solo referencia) | 0,900 |
| Distribución esperada 2024 (D1 / D5 / D3) | 72,3 % / 17,0 % / 8,2 % |

## Citar

```bibtex
@unpublished{cruzcruz_trayectorias,
  title  = {Trayectorias post-deforestaci{\'o}n en la Amazon{\'\i}a peruana (2021--2025): destinos de cobertura,
            trayectorias plurianuales y predicci{\'o}n con Random Forest a partir de alertas verificadas de MapBiomas},
  author = {Cruz Cruz, Erik Gianmarco},
  note   = {Manuscrito enviado},
  url    = {https://github.com/Erikcruz1234/trayectorias-postdeforestacion-peru}
}
```
