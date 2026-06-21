# Output schema · Drawing v2

## Archivos generados

```text
/home/pi/data/sessions/Sxx/output/
├── drawing.svg
├── preview.png
├── metadata.json
└── generation_log.json
```

## `drawing.svg`

- dibujo vectorial principal;
- unidades en milímetros;
- trayectoria continua;
- apto para mecanismo sin eje Z.

## `preview.png`

- preview raster del dibujo;
- sirve para revisar rápidamente si la escena se parece a las fotos.

## `metadata.json`

Incluye:

- fotos usadas;
- lecturas ambientales usadas;
- parámetros visuales derivados del ambiente;
- datos del análisis de imagen;
- datos del raster tonal y contornos.

