// ══════════════════════════════════════════════════════════════════════════════
// SCRIPT 03 — TRAYECTORIAS T+2 Y T+3 PARA ALERTAS 2021
// ══════════════════════════════════════════════════════════════════════════════
//
// Propósito : Para las alertas del año 2021 (único año con seguimiento
//             completo hasta T+3 en la Colección 3.0), extrae la cobertura
//             modal en T+2 (2023) y T+3 (2024) y clasifica el destino.
//             Permite construir las trayectorias dinámicas plurianuales.
//
// Entradas  : alertas_con_trayectoria (Asset GEE — generado por script 01)
//             MapBiomas Perú Colección 3.0
//
// Salidas   : alertas_2021_T2_T3.csv en Google Drive
//
// Autor     : Erik Gianmarco Cruz Cruz
// ══════════════════════════════════════════════════════════════════════════════

var CFG = {
  anioAlerta    : 2021,
  anioT2        : 2023,
  anioT3        : 2024,
  assetAlertas  : 'projects/tesis-481703/assets/alertas_con_trayectoria',
  assetMapBiomas: 'projects/mapbiomas-public/assets/peru/collection3/' +
                  'mapbiomas_peru_collection3_integration_v1',
  escala        : 30,
  tileScale     : 4,
  driveFolder   : 'Proyecto_MapBiomas',
  exportName    : 'alertas_2021_T2_T3'
};

var alertas2021 = ee.FeatureCollection(CFG.assetAlertas)
  .filter(ee.Filter.eq('ani_lrt', CFG.anioAlerta));

print('Alertas 2021 cargadas:', alertas2021.size());

var mapbiomas    = ee.Image(CFG.assetMapBiomas);
var coberturaT2  = mapbiomas.select('classification_' + CFG.anioT2).rename('cobertura_T2');
var coberturaT3  = mapbiomas.select('classification_' + CFG.anioT3).rename('cobertura_T3');
var stack        = coberturaT2.addBands(coberturaT3);

// Clasificación de destino (misma lógica que script 01)
function claseADestino(claseNum) {
  return ee.Algorithms.If(
    ee.List([3, 4, 6, 68, 12, 13, 66]).contains(claseNum), 'D5_bosque',
  ee.Algorithms.If(
    ee.List([15, 18, 21, 70, 72, 20]).contains(claseNum),  'D1_agricultura',
  ee.Algorithms.If(
    ee.List([30]).contains(claseNum),                       'D2b_mineria',
  ee.Algorithms.If(
    ee.List([25, 23]).contains(claseNum),                   'D3_suelo_expuesto',
  ee.Algorithms.If(
    ee.List([40, 11]).contains(claseNum),                   'D4_regeneracion',
    'otros'
  )))));
}

var alertasConT2T3 = alertas2021.map(function(feature) {
  var stats = stack.reduceRegion({
    reducer:   ee.Reducer.mode(),
    geometry:  feature.geometry(),
    scale:     CFG.escala,
    tileScale: CFG.tileScale,
    maxPixels: 1e9
  });

  var claseT2raw = ee.Number(
    ee.Algorithms.If(stats.contains('cobertura_T2'), stats.get('cobertura_T2'), -1)
  ).int();
  var claseT3raw = ee.Number(
    ee.Algorithms.If(stats.contains('cobertura_T3'), stats.get('cobertura_T3'), -1)
  ).int();

  var destinoT2 = ee.String(
    ee.Algorithms.If(claseT2raw.eq(-1), 'sin_dato', claseADestino(claseT2raw))
  );
  var destinoT3 = ee.String(
    ee.Algorithms.If(claseT3raw.eq(-1), 'sin_dato', claseADestino(claseT3raw))
  );

  return feature.set({
    'clase_T2_raw': claseT2raw,
    'destino_T2':   destinoT2,
    'clase_T3_raw': claseT3raw,
    'destino_T3':   destinoT3
  });
});

print('Distribución destino_T2 (2023):', alertasConT2T3.aggregate_histogram('destino_T2'));
print('Distribución destino_T3 (2024):', alertasConT2T3.aggregate_histogram('destino_T3'));

Export.table.toDrive({
  collection:     alertasConT2T3,
  description:    CFG.exportName,
  fileNamePrefix: CFG.exportName,
  folder:         CFG.driveFolder,
  fileFormat:     'CSV',
  selectors: [
    'alert_d', 'ani_lrt', 'dprtmnt',
    'area_ha', 'log_are', 'dist_via_k', 'log_dist_v',
    'tip_lrt', 'tip_mcr', 'clase_T1', 'destino', 'gini',
    'flag_excluir', 'flag_mixta', 'flag_sin_T1p',
    'clase_T2_raw', 'destino_T2',
    'clase_T3_raw', 'destino_T3'
  ]
});

print('✅ Task enviada → Tasks → Run');
