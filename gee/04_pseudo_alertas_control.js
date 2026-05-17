// ══════════════════════════════════════════════════════════════════════════════
// SCRIPT 04 — PSEUDO-ALERTAS: GRUPO CONTROL
// ══════════════════════════════════════════════════════════════════════════════
//
// Propósito : Genera n=2000 pseudo-alertas en bosque no perturbado (2020)
//             que no recibieron ninguna alerta verificada entre 2021–2023.
//             Permite calibrar el IESA (Índice de Estado Post-Alerta) y
//             cuantificar el impacto real de la perturbación vs. la línea
//             base de bosque sin intervención detectada.
//
// Máscara aplicada:
//   (1) Cobertura 2020 = bosque primario (clase 3) o formación natural (clase 4)
//   (2) Sin alerta MapBiomas verificada en el perímetro 2021–2023
//   (3) Muestreo aleatorio estratificado a escala 500 m, semilla = 42
//
// Tasa de rechazo esperada: ~36% (puntos que caen fuera de la máscara)
// Puntos obtenidos: n = 1,273 de 2,000 solicitados
//
// Salida: pseudo_alertas_control.csv en Google Drive
//
// Autor: Erik Gianmarco Cruz Cruz
// ══════════════════════════════════════════════════════════════════════════════

var MB      = ee.Image(
  "projects/mapbiomas-public/assets/peru/collection3/" +
  "mapbiomas_peru_collection3_integration_v1"
);
var ALERTAS = ee.FeatureCollection(
  "projects/tesis-481703/assets/alertas_con_trayectoria"
);

var N_PUNTOS = 2000;
var SEMILLA  = 42;   // semilla fija para reproducibilidad

// ── Área de estudio: nueve departamentos amazónicos ───────────────────────────
var amazonia = ee.FeatureCollection("FAO/GAUL/2015/level1")
  .filter(ee.Filter.eq('ADM0_NAME', 'Peru'))
  .filter(ee.Filter.inList('ADM1_NAME', [
    'Loreto','Ucayali','Madre de Dios','San Martin',
    'Huanuco','Pasco','Junin','Amazonas','Cusco'
  ]));
var aoi = amazonia.geometry();

// ── Máscara: bosque 2020 sin alertas verificadas ──────────────────────────────
var bosque2020 = MB.select('classification_2020')
  .eq(3).or(MB.select('classification_2020').eq(4));

// Rasterizar alertas para excluir zonas perturbadas
var alertas_raster = ALERTAS
  .reduceToImage(['alert_d'], ee.Reducer.count())
  .unmask(0).eq(0);   // 1 = sin alerta registrada

var mascara = bosque2020.and(alertas_raster).selfMask().rename('bosque');

// ── Muestreo ──────────────────────────────────────────────────────────────────
var puntos = mascara.sample({
  region:     aoi,
  scale:      500,
  numPixels:  N_PUNTOS,
  seed:       SEMILLA,
  geometries: true
});

print('Puntos generados (tras máscara):', puntos.size());
// Esperado: ~1,273 (tasa de rechazo ~36.4%)

// ── Clasificación de destino ──────────────────────────────────────────────────
function claseADestino(img, anio, geom) {
  var stats = img.select('classification_' + anio)
    .reduceRegion({
      reducer:   ee.Reducer.mode(),
      geometry:  geom.buffer(100),
      scale:     30,
      maxPixels: 1e6
    });
  var key   = 'classification_' + anio;
  var valor = ee.Number(
    ee.Algorithms.If(stats.contains(key), stats.get(key), -1)
  );
  return ee.String(
    ee.Algorithms.If(valor.eq(3).or(valor.eq(4)),    'D5_bosque',
    ee.Algorithms.If(valor.eq(15).or(valor.eq(18))
                       .or(valor.eq(21)),             'D1_agricultura',
    ee.Algorithms.If(valor.eq(30),                   'D2_mineria',
    ee.Algorithms.If(valor.eq(25),                   'D3_suelo_expuesto',
    ee.Algorithms.If(valor.eq(41),                   'D4_regeneracion',
    'otros')))))
  );
}

// ── Extracción T+1, T+2, T+3 para cada pseudo-alerta ─────────────────────────
var pseudo = puntos.map(function(f) {
  var geom = f.geometry();
  var d1   = claseADestino(MB, 2022, geom);  // T+1 (año base: 2021)
  var d2   = claseADestino(MB, 2023, geom);  // T+2
  var d3   = claseADestino(MB, 2024, geom);  // T+3

  var iesa1 = ee.Number(ee.Algorithms.If(d1.equals('D5_bosque'), 1, 0));
  var iesa2 = ee.Number(ee.Algorithms.If(d2.equals('D5_bosque'), 1, 0));
  var iesa3 = ee.Number(ee.Algorithms.If(d3.equals('D5_bosque'), 1, 0));

  return f.set({
    'tipo'      : 'pseudo_alerta',
    'destino_T1': d1, 'destino_T2': d2, 'destino_T3': d3,
    'iesa_T1'   : iesa1, 'iesa_T2': iesa2, 'iesa_T3': iesa3
  });
});

// ── Validación en consola ─────────────────────────────────────────────────────
print('Distribución T+1:', pseudo.aggregate_histogram('destino_T1'));
print('IESA T+1 (media, esperado ~0.99):', pseudo.aggregate_mean('iesa_T1'));
print('IESA T+2 (media, esperado ~0.99):', pseudo.aggregate_mean('iesa_T2'));
print('IESA T+3 (media, esperado ~0.99):', pseudo.aggregate_mean('iesa_T3'));

// ── Exportación ───────────────────────────────────────────────────────────────
Export.table.toDrive({
  collection:     pseudo,
  description:    'pseudo_alertas_control',
  folder:         'Proyecto_MapBiomas',
  fileNamePrefix: 'pseudo_alertas_control',
  fileFormat:     'CSV',
  selectors: [
    'tipo',
    'destino_T1', 'destino_T2', 'destino_T3',
    'iesa_T1',    'iesa_T2',    'iesa_T3'
  ]
});

print('✅ Task enviada → pestaña Tasks → Run');
