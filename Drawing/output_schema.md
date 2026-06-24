# Output schema · Drawing v4 30x32

## Archivos generados

```text
/home/pi/data/sessions/Sxx/output/
├── drawing.svg
├── drawing.gcode
├── preview.png
├── metadata.json
├── generation_log.json
└── process_steps/
```

## `drawing.svg`

- dibujo vectorial principal;
- unidades en milímetros;
- tamaño por defecto de 30 mm x 32 mm;
- trayectoria continua pensada para un sistema sin eje Z.

## `preview.png`

- previsualización rápida del dibujo;
- sirve para comparar si el resultado se siente legible antes de mandar a la máquina.

## `drawing.gcode`

- G-code compatible con GRBL;
- unidades en milímetros;
- coordenadas absolutas;
- área de trabajo por defecto de 30 mm x 32 mm;
- modo de Y por defecto: `direct`;
- esquina inicial de referencia por defecto: `top_right`;
- requiere homing antes de ejecutarse;
- no manda `$H` por sí mismo.

En modo `direct`, el generador escribe:

```text
Y_gcode = Y_dibujo
```

Si se necesita invertir Y, usar:

```text
--gcode-y-mode flip
```

## `metadata.json`

Incluye:

- fotos utilizadas;
- lecturas ambientales utilizadas;
- parámetros derivados del ambiente;
- análisis de imagen;
- datos de bandas, contornos y líneas internas.
- ruta del archivo G-code generado.
- modo de transformación Y usado para G-code.

## `process_steps/`

Incluye imágenes y archivos JSON secuenciales para revisar cómo se transformó la imagen antes de llegar al SVG final.

> Esta versión usa el estilo `contraespacios_svg_v4_30x32_legible` y conserva la salida JSON usada por Node-RED.
