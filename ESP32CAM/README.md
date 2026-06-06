# ESP32

Para este proyecto se hace uso de un ESP WROOM 32, compatible con un ESP32 DevKit V1, el cual se programa a través de la IDE de Arduino. Se recomienda hacer dicha instalación en un equipo Windows, Linux o Mac. La documentación para instalar el Core de Espressif se encuentra en el siguiente [enlace](https://docs.espressif.com/projects/arduino-esp32/en/latest/installing.html).

```
https://docs.espressif.com/projects/arduino-esp32/en/latest/installing.html
```

## Hardware

- ESP32 DevKit V1
- Sensor ENS160+AHT21

## Software

- Arduino IDE
- Espressif Core para Arduino IDE

## Bibliotecas

- SparkFun ENS160 Arduino Library
- Adafruit AHTX0
- PubSubClient (Nick O’Leary)
- ArduinoJson (Benoit Blanchon)

## Conexiones

La conexión del sensor es de la siguiente forma

```
ENS160+AHT21    ESP32
--------------------------
VCC ----------> 3.3V
GND ----------> GND
SDA ----------> SDA/GPIO21
SCL ----------> SCL/GPIO22
```

## Observaciones

- El programa que envía los datos desde el micro controlador hasta la Raspberry Pi via MQTT es `02_MQTT_ENS160_AHT21`. Este programa debe ser modificado para que se conecte a la red de la Raspberry Pi, a la IP adecuada.

- El intervalo de envío es de 30 segundos, puede ser ajustado desde el mismo programa. 