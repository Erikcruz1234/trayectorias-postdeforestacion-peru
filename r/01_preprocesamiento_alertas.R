# ══════════════════════════════════════════════════════════════════════════════
# SCRIPT R — PREPROCESAMIENTO Y LIMPIEZA DE ALERTAS MAPBIOMAS
# ══════════════════════════════════════════════════════════════════════════════
#
# Propósito : Lee el shapefile de alertas MapBiomas Alerta Perú,
#             aplica filtros de calidad, estandariza columnas, crea variables
#             derivadas y exporta los archivos necesarios para el modelo en
#             Google Colab.
#
# Entradas  : dashboard_alerts_shapefile.shp (descargado de MapBiomas Alerta Perú)
# Salidas   : mapbiomas_final.gpkg    — dataset completo con geometría
#             mapbiomas_modelo.csv    — subset 2021–2022 para entrenamiento RF
#             mapbiomas_desc.csv      — subset 2021–2023 para análisis descriptivo
#             summary_stats.csv       — estadísticas agregadas por año
#             kruskal_resultado.txt   — test Kruskal-Wallis de área por año
#
# Autor     : Erik Gianmarco Cruz Cruz
# Afiliación: Universidad Nacional Mayor de San Marcos
# ══════════════════════════════════════════════════════════════════════════════

library(sf)
library(dplyr)
library(lubridate)
library(ggplot2)

# ── RUTAS (ajustar según entorno local) ───────────────────────────────────────
RUTA_RAW    <- "data/raw/dashboard_alerts-shapefile/dashboard_alerts_shapefile.shp"
RUTA_SALIDA <- "data/clean/"
dir.create(RUTA_SALIDA, recursive = TRUE, showWarnings = FALSE)

# ── 1. CARGAR SHAPEFILE ───────────────────────────────────────────────────────
cat("Cargando shapefile...\n")
mapbiomas <- read_sf(RUTA_RAW)

cat("Columnas originales:\n")
print(names(mapbiomas))
cat("\nTipos de presión únicos:\n")
print(unique(mapbiomas$vpressao))
cat("\nTotal registros brutos:", nrow(mapbiomas), "\n")

# ── 2. RENOMBRE Y LIMPIEZA ────────────────────────────────────────────────────
mapbiomas_clean <- mapbiomas %>%
  rename(
    alert_id     = codealerta,
    area_ha      = areaha,
    anio_alerta  = anodetec,
    fecha_alerta = datadetec,
    tipo_alerta  = vpressao,
    departamento = amazregion
  ) %>%
  mutate(
    # Limpiar fechas
    fecha_alerta = ymd(fecha_alerta),

    # Filtro de área mínima (≥ 0.5 ha, según metodología MapBiomas)
    # Aplicado a continuación con filter()

    # Variables logarítmicas (reducen sesgo por distribución asimétrica del área)
    log_area = log(area_ha),

    # Agrupación macro de tipos de presión
    tipo_macro = case_when(
      tipo_alerta %in% c("agriculture", "mining", "ilegal_mining",
                         "roads", "urban_expansion") ~ "antropico_directo",
      tipo_alerta %in% c("natural_cause", "others")  ~ "disturbio_indirecto",
      TRUE ~ "otro"
    )
  ) %>%
  filter(area_ha >= 0.5)

cat("\nRegistros tras filtro área ≥ 0.5 ha:", nrow(mapbiomas_clean), "\n")

# ── 3. CORRECCIÓN DE GEOMETRÍAS ───────────────────────────────────────────────
mapbiomas_clean <- mapbiomas_clean %>%
  mutate(geometry = st_make_valid(geometry))

n_invalidos <- sum(!st_is_valid(mapbiomas_clean))
cat("Geometrías inválidas tras corrección:", n_invalidos, "\n")

# Extraer solo polígonos (descartar GeometryCollections)
mapbiomas_clean <- mapbiomas_clean %>%
  st_collection_extract("POLYGON")

# Proyección UTM 18S (Amazonía peruana)
mapbiomas_clean <- st_transform(mapbiomas_clean, 32718)

# ── 4. SELECCIÓN DE COLUMNAS FINALES ─────────────────────────────────────────
mapbiomas_final <- mapbiomas_clean %>%
  select(
    alert_id, anio_alerta, fecha_alerta,
    area_ha, log_area,
    tipo_alerta, tipo_macro,
    departamento,
    geometry
  )

cat("\nEstructura del dataset final:\n")
str(mapbiomas_final)

# ── 5. ESTADÍSTICAS DESCRIPTIVAS POR AÑO ─────────────────────────────────────
summary_stats <- mapbiomas_final %>%
  st_drop_geometry() %>%
  group_by(anio_alerta) %>%
  summarise(
    n_alertas  = n(),
    area_total = sum(area_ha,  na.rm = TRUE),
    area_media = mean(area_ha, na.rm = TRUE),
    area_med   = median(area_ha, na.rm = TRUE),
    .groups    = "drop"
  )

cat("\nEstadísticas por año:\n")
print(summary_stats)

# ── 6. TEST KRUSKAL-WALLIS (variación de área entre años) ────────────────────
kw_test <- kruskal.test(area_ha ~ as.factor(anio_alerta),
                         data = mapbiomas_final)
cat("\nTest Kruskal-Wallis:\n")
print(kw_test)

# ── 7. EXPORTACIÓN ───────────────────────────────────────────────────────────
# Dataset completo con geometría
st_write(mapbiomas_final,
         paste0(RUTA_SALIDA, "mapbiomas_final.gpkg"),
         delete_layer = TRUE)

# CSV sin geometría (para Colab)
write.csv(st_drop_geometry(mapbiomas_final),
          paste0(RUTA_SALIDA, "mapbiomas_final.csv"),
          row.names = FALSE)

# Subset modelo (2021–2022, para entrenamiento RF)
mapbiomas_modelo <- mapbiomas_final %>%
  filter(anio_alerta %in% c(2021, 2022))
write.csv(st_drop_geometry(mapbiomas_modelo),
          paste0(RUTA_SALIDA, "mapbiomas_modelo.csv"),
          row.names = FALSE)

# Subset descriptivo (2021–2023)
mapbiomas_desc <- mapbiomas_final %>%
  filter(anio_alerta %in% c(2021, 2022, 2023))
write.csv(st_drop_geometry(mapbiomas_desc),
          paste0(RUTA_SALIDA, "mapbiomas_desc.csv"),
          row.names = FALSE)

# Estadísticas
write.csv(summary_stats,
          paste0(RUTA_SALIDA, "summary_stats.csv"),
          row.names = FALSE)

# Resultado test
sink(paste0(RUTA_SALIDA, "kruskal_resultado.txt"))
print(kw_test)
sink()

cat("\n✅ Exportación completa en:", RUTA_SALIDA, "\n")
cat("   mapbiomas_final.gpkg    — dataset completo\n")
cat("   mapbiomas_final.csv     — para análisis en Colab\n")
cat("   mapbiomas_modelo.csv    — subset 2021-2022 para RF\n")
cat("   mapbiomas_desc.csv      — subset 2021-2023 descriptivo\n")
cat("   summary_stats.csv       — estadísticas por año\n")
cat("   kruskal_resultado.txt   — test estadístico\n")
