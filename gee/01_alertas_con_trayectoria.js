// ══════════════════════════════════════════════════════════════════════════════
// SCRIPT 01 — ALERTAS CON TRAYECTORIA POST-DEFORESTACIÓN (T−1, T+1)
// ══════════════════════════════════════════════════════════════════════════════
//
// Propósito : Para cada alerta verificada de MapBiomas Alerta Perú,
//             extrae la clase de cobertura modal en T−1 (año anterior a la
//             alerta) y T+1 (año siguiente), calcula el índice Gini de
//             heterogeneidad interna del polígono en T+1, y clasifica el
//             destino post-deforestación en cinco categorías (D1–D5).
//
// Entradas  : alertas_con_distancia (Asset GEE — generado por script 02)
//             MapBiomas Perú Colección 3.0 (asset público)
//
// Salidas   : alertas_con_trayectoria (Asset GEE + CSV en Drive)
//
// Autor     : Erik Gianmarco Cruz Cruz
// Afiliación: Universidad Nacional Mayor de San Marcos
// Proyecto  : trayectorias-postdeforestacion-peru
// ══════════════════════════════════════════════════════════════════════════════

// ── 0. CONFIGURACIÓN ─────────────────────────────────────────────────────────
var alertas = ee.FeatureCollection("projects/tesis-481703/assets/alertas_con_distancia");
var AÑO_MAX = 2024;
var mapbiomas = ee.Image(
  "projects/mapbiomas-public/assets/peru/collection3/mapbiomas_peru_collection3_integration_v1"
);

print("Total alertas:", alertas.size());
print("Bandas MapBiomas:", mapbiomas.bandNames());

// ── 1. FUNCIÓN: clase modal dentro de un polígono ─────────────────────────────
// Retorna -1 si el año está fuera del rango disponible (2019–2024).
function getModal(feature, anio) {
  var anioNum = ee.Number(anio).int();
  var dentroRango = anioNum.gte(2019).and(anioNum.lte(AÑO_MAX));

  var banda = ee.Algorithms.If(
    dentroRango,
    mapbiomas.select(ee.String("classification_").cat(anioNum.format())),
    ee.Image.constant(-1).rename("classification_0")
  );

  var stats = ee.Image(banda).reduceRegion({
    reducer:   ee.Reducer.mode(),
    geometry:  feature.geometry(),
    scale:     30,
    maxPixels: 1e9
  });

  return ee.Number(stats.values().get(0)).int();
}

// ── 2. CLASIFICACIÓN T−1: tipo de cobertura previa ───────────────────────────
// Solo se incluyen alertas donde T−1 es bosque (clase 3, 4, 6, 68) o
// vegetación secundaria (clase 40). Las demás se marcan como "otros" y
// se excluyen del análisis (flag_excluir = 1).
function clasificarT1(claseRaw) {
  return ee.Algorithms.If(claseRaw.eq(3),  "bosque_primario",
         ee.Algorithms.If(claseRaw.eq(4),  "formacion_natural",
         ee.Algorithms.If(claseRaw.eq(6),  "formacion_natural",
         ee.Algorithms.If(claseRaw.eq(68), "formacion_natural",
         ee.Algorithms.If(claseRaw.eq(40), "vegetacion_secundaria",
         ee.Algorithms.If(claseRaw.eq(-1), "sin_dato",
         "otros"))))));
}

// ── 3. CLASIFICACIÓN T+1: destino post-deforestación ─────────────────────────
// D1 Agricultura  : pastizales (15), cultivos (18/21), mosaico agropecuario (70,72,20)
// D2 Minería      : minería (30)
// D3 Suelo expuesto: área desnuda (25), playa/duna (23)
// D4 Regeneración : vegetación secundaria (40), campo abierto (11)
// D5 Bosque       : formaciones boscosas (3,4,6,68,12,13,66)
function clasificarDestino(claseRaw) {
  var agri  = ee.List([15, 21, 70, 72, 20]);
  var mine  = ee.List([30]);
  var suelo = ee.List([25, 23]);
  var regen = ee.List([40, 11]);
  var bosq  = ee.List([3, 4, 6, 68, 12, 13, 66]);

  return ee.Algorithms.If(agri.contains(claseRaw),  "D1_agricultura",
         ee.Algorithms.If(mine.contains(claseRaw),  "D2b_mineria",
         ee.Algorithms.If(suelo.contains(claseRaw), "D3_suelo_expuesto",
         ee.Algorithms.If(regen.contains(claseRaw), "D4_regeneracion",
         ee.Algorithms.If(bosq.contains(claseRaw),  "D5_bosque",
         "otros")))));
}

// ── 4. ÍNDICE GINI DE HETEROGENEIDAD INTERNA ─────────────────────────────────
// Gini = 1 − Σ pᵢ²
// Gini = 0 → polígono completamente homogéneo (un solo uso de suelo)
// Gini → 1 → destino mixto (múltiples clases dentro del polígono)
// NOTA: Este Gini es una variable predictora del analista, distinto del
//       criterio de impureza Gini interno del Random Forest.
function calcularGini(feature, anioT1p) {
  var anioNum = ee.Number(anioT1p).int();
  var dentroRango = anioNum.gte(2019).and(anioNum.lte(AÑO_MAX));

  var banda = ee.Algorithms.If(
    dentroRango,
    mapbiomas.select(ee.String("classification_").cat(anioNum.format())),
    ee.Image.constant(-1).rename("classification_0")
  );

  var hist = ee.Dictionary(
    ee.Image(banda).reduceRegion({
      reducer:   ee.Reducer.frequencyHistogram(),
      geometry:  feature.geometry(),
      scale:     30,
      maxPixels: 1e9
    }).values().get(0)
  );

  var total = ee.Number(hist.values().reduce(ee.Reducer.sum()));
  var sumaCuadrados = hist.values()
    .map(function(v) {
      var p = ee.Number(v).divide(total);
      return p.pow(2);
    })
    .reduce(ee.Reducer.sum());

  return ee.Number(1).subtract(ee.Number(sumaCuadrados));
}

// ── 5. FUNCIÓN MAP PRINCIPAL ──────────────────────────────────────────────────
var alertasConTrayectoria = alertas.map(function(feature) {
  var anioAlerta = ee.Number(feature.get("ani_lrt")).int();
  var anioT1     = anioAlerta.subtract(1);   // año previo
  var anioT1p    = anioAlerta.add(1);        // año siguiente

  // T−1
  var claseT1raw = getModal(feature, anioT1);
  var claseT1    = clasificarT1(claseT1raw);
  var flagExcluir = ee.Algorithms.If(
    ee.String(claseT1).equals("otros").or(ee.String(claseT1).equals("sin_dato")),
    1, 0
  );

  // T+1
  var tieneTp1    = anioT1p.lte(AÑO_MAX);
  var claseT1pRaw = ee.Algorithms.If(tieneTp1, getModal(feature, anioT1p), -1);
  var destino     = ee.Algorithms.If(
    tieneTp1,
    clasificarDestino(ee.Number(claseT1pRaw)),
    "sin_T1p"
  );
  var flagSinT1p = ee.Algorithms.If(tieneTp1, 0, 1);

  // Gini
  var gini = ee.Algorithms.If(
    tieneTp1,
    calcularGini(feature, anioT1p),
    ee.Number(-1)
  );
  var flagMixta = ee.Algorithms.If(ee.Number(gini).gt(0.5), 1, 0);

  return feature.set({
    "clase_T1":     claseT1,
    "clase_T1_raw": claseT1raw,
    "clase_Tplus1": claseT1pRaw,
    "destino":      destino,
    "gini":         gini,
    "flag_mixta":   flagMixta,
    "flag_excluir": flagExcluir,
    "flag_sin_T1p": flagSinT1p
  });
});

// ── 6. VALIDACIÓN EN CONSOLA ──────────────────────────────────────────────────
print("Distribución clase_T1:",  alertasConTrayectoria.aggregate_histogram("clase_T1"));
print("Distribución destino:",   alertasConTrayectoria.aggregate_histogram("destino"));
print("Flag excluir (n):",       alertasConTrayectoria.aggregate_sum("flag_excluir"));
print("Flag sin T+1 (n):",       alertasConTrayectoria.aggregate_sum("flag_sin_T1p"));

// ── 7. EXPORTACIÓN ───────────────────────────────────────────────────────────
Export.table.toDrive({
  collection:     alertasConTrayectoria,
  description:    "alertas_con_trayectoria_csv",
  folder:         "Proyecto_MapBiomas",
  fileNamePrefix: "alertas_con_trayectoria",
  fileFormat:     "CSV",
  selectors: [
    "alert_d", "ani_lrt", "area_ha", "log_are",
    "dist_via_km", "log_dist_via",
    "clase_T1", "clase_T1_raw",
    "clase_Tplus1", "destino",
    "gini", "flag_mixta", "flag_excluir", "flag_sin_T1p"
  ]
});

Export.table.toAsset({
  collection:  alertasConTrayectoria,
  description: "alertas_con_trayectoria_asset",
  assetId:     "projects/tesis-481703/assets/alertas_con_trayectoria"
});

print("✅ Tasks enviadas → revisar en Tasks panel");
