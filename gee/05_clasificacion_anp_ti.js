// ══════════════════════════════════════════════════════════════════════════════
// SCRIPT 05 — CLASIFICACIÓN DE ALERTAS POR CATEGORÍA ANP Y TERRITORIO INDÍGENA
// ══════════════════════════════════════════════════════════════════════════════
//
// Propósito : Asigna a cada alerta su categoría de contexto institucional:
//             (a) ANP: intangible, uso directo, buffer 5 km, buffer 10 km,
//                 o fuera de ANP
//             (b) TI:  titulada, en proceso, o fuera de TI
//
// Fuentes   : WDPA (World Database on Protected Areas) via GEE
//             IBC 2024 (asset privado en el proyecto GEE del autor)
//
// Salida    : alertas_con_anp_ti.csv en Google Drive
//
// Autor     : Erik Gianmarco Cruz Cruz
// ══════════════════════════════════════════════════════════════════════════════

// ── 1. CARGAR DATOS ───────────────────────────────────────────────────────────
var alertas  = ee.FeatureCollection('projects/tesis-481703/assets/alertas_con_distancia');
var wdpa_raw = ee.FeatureCollection('WCMC/WDPA/current/polygons');

// ── 2. FILTRAR WDPA PARA PERÚ ────────────────────────────────────────────────
var wdpa = wdpa_raw
  .filter(ee.Filter.eq('ISO3', 'PER'))
  .filter(ee.Filter.neq('MARINE', 2))
  .filter(ee.Filter.gt('GIS_AREA', 0));

// Categorías IUCN → tipo ANP
// Intangibles: Ia (reserva estricta), Ib (wilderness), II (parque nacional)
// Uso directo: III–VI (monumento, hábitat, paisaje, uso sostenible)
var anp_intangible  = wdpa.filter(ee.Filter.inList('IUCN_CAT', ['Ia', 'Ib', 'II']));
var anp_uso_directo = wdpa.filter(ee.Filter.inList('IUCN_CAT', ['III','IV','V','VI']));
var anp_total       = anp_intangible.merge(anp_uso_directo);

// Disolver + simplificar para evitar errores de borde en contains()
var geom_intangible  = anp_intangible.geometry().simplify(200);
var geom_uso_directo = anp_uso_directo.geometry().simplify(200);
var geom_anp_total   = anp_total.geometry().simplify(200);

// Buffers de zona de amortiguamiento
var buffer_5km  = geom_anp_total.buffer(5000,  500).simplify(200);
var buffer_10km = geom_anp_total.buffer(10000, 500).simplify(200);

// ── 3. CLASIFICACIÓN POR ANP ──────────────────────────────────────────────────
// Jerarquía: intangible > uso_directo > buffer_5km > buffer_10km > fuera_anp
// Una alerta dentro de una ANP intangible NO se clasifica también en uso_directo
var clasificarANP = function(feature) {
  var punto = feature.geometry();
  var en_intangible  = geom_intangible.contains(punto,  100);
  var en_uso_directo = geom_uso_directo.contains(punto, 100);
  var en_buffer_5    = buffer_5km.contains(punto,       100);
  var en_buffer_10   = buffer_10km.contains(punto,      100);

  var categoria = ee.Algorithms.If(
    en_intangible,  'dentro_intangible',
    ee.Algorithms.If(
      en_uso_directo, 'dentro_uso_directo',
      ee.Algorithms.If(
        en_buffer_5,  'buffer_5km',
        ee.Algorithms.If(
          en_buffer_10, 'buffer_10km',
          'fuera_anp'
        )
      )
    )
  );

  // Variable binaria para la regresión logística (dentro_ANP = 1)
  var dentro_anp = ee.Algorithms.If(
    ee.String(categoria).equals('fuera_anp'), 0, 1
  );

  return feature.set({
    'anp_categoria': categoria,
    'dentro_ANP':    dentro_anp
  });
};

var alertas_con_anp = alertas.map(clasificarANP);

// ── 4. VALIDACIÓN ─────────────────────────────────────────────────────────────
Map.setCenter(-75.0, -9.5, 6);
print('Conteo por categoría ANP:',
      alertas_con_anp.aggregate_histogram('anp_categoria'));

// ── 5. EXPORTACIÓN ───────────────────────────────────────────────────────────
Export.table.toDrive({
  collection:     alertas_con_anp,
  description:    'alertas_con_anp_ti',
  fileNamePrefix: 'alertas_con_anp_ti',
  fileFormat:     'CSV',
  selectors:      null   // exporta todas las columnas
});

print('✅ Task enviada → Tasks → Run');
