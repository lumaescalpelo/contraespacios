# Output schema · Drawing

Archivos generados dentro de:

```text
/home/pi/data/sessions/Sxx/output/
```

## `drawing.svg`

Dibujo vectorial principal.

- Unidades: milímetros.
- ViewBox: coincide con el área física configurada.
- Default: `0 0 16 43`.
- Trazo: continuo.
- Requiere eje Z: no.

## `preview.png`

Imagen raster para revisar el resultado.

## `metadata.json`

Contiene:

```json
{
  "ok": true,
  "session_id": "S01",
  "algorithm": "contraespacios_svg_v1",
  "film": {
    "width_mm": 16,
    "height_mm": 43,
    "coordinate_space": "millimeters",
    "continuous_path": true,
    "z_axis_required": false
  },
  "inputs": {
    "photos_used": 3,
    "environment_readings_used": 3
  },
  "environment": {},
  "visual_parameters": {},
  "image_analysis": {},
  "outputs": {}
}
```

## `generation_log.json`

Resumen corto de ejecución para depuración y Node-RED.
