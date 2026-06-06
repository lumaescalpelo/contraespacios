#include <Wire.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#include <Adafruit_AHTX0.h>
#include <SparkFun_ENS160.h>

// --------- I2C (ESP32 DevKit V1) ----------
static const int I2C_SDA = 21;
static const int I2C_SCL = 22;

// --------- WiFi ----------
const char* WIFI_SSID = "cinema";
const char* WIFI_PASS = "barredura";

// --------- MQTT ----------
const char* MQTT_HOST = "192.168.1.105";
const uint16_t MQTT_PORT = 1883;

// Topic sugerido (cámbialo a lo que quieras)
const char* MQTT_TOPIC = "ambiente/lectura";

// Si quieres identificar el dispositivo (útil para Node-RED), puedes incluirlo en topic o payload
// const char* DEVICE_ID = "esp32-aire-01";

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

// --------- Sensores ----------
Adafruit_AHTX0 aht;
SparkFun_ENS160 ens;

// --------- Timing ----------
unsigned long lastSend = 0;
const unsigned long SEND_INTERVAL_MS = 30000;

void i2cScan() {
  Serial.println("\nI2C scan:");
  byte count = 0;
  for (byte addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.print("  Found 0x");
      if (addr < 16) Serial.print('0');
      Serial.println(addr, HEX);
      count++;
      delay(2);
    }
  }
  if (count == 0) Serial.println("  No I2C devices found.");
  Serial.println();
}

void wifiConnect() {
  Serial.print("Conectando a WiFi: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
    if (millis() - start > 20000) { // 20s timeout
      Serial.println("\nWiFi timeout. Reintentando...");
      start = millis();
      WiFi.disconnect(true);
      delay(200);
      WiFi.begin(WIFI_SSID, WIFI_PASS);
    }
  }

  Serial.println("\nWiFi conectado.");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

void mqttConnect() {
  mqtt.setServer(MQTT_HOST, MQTT_PORT);

  while (!mqtt.connected()) {
    Serial.print("Conectando a MQTT ");
    Serial.print(MQTT_HOST);
    Serial.print(":");
    Serial.print(MQTT_PORT);
    Serial.print(" ... ");

    // ClientID único (usa MAC)
    String clientId = "esp32-ens160-";
    clientId += String((uint32_t)ESP.getEfuseMac(), HEX);

    if (mqtt.connect(clientId.c_str())) {
      Serial.println("OK");
    } else {
      Serial.print("FAIL rc=");
      Serial.print(mqtt.state());
      Serial.println(" reintento en 2s");
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(200);

  // I2C init
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(400000);

  Serial.println("ENS160 + AHT2x + WiFi + MQTT");
  i2cScan();

  // Sensores
  if (!aht.begin(&Wire)) {
    Serial.println("ERROR: No se detecta AHT2x.");
    while (1) delay(100);
  }
  Serial.println("AHT2x OK");

  if (!ens.begin(Wire, 0x53)) {
    Serial.println("ENS160 no responde en 0x53, probando 0x52...");
    if (!ens.begin(Wire, 0x52)) {
      Serial.println("ERROR: No se detecta ENS160.");
      while (1) delay(100);
    }
  }
  Serial.println("ENS160 OK");

  ens.setOperatingMode(SFE_ENS160_RESET);
  delay(10);
  ens.setOperatingMode(SFE_ENS160_STANDARD);

  // WiFi + MQTT
  wifiConnect();
  mqttConnect();

  Serial.println("Inicialización completa.\n");
}

bool readSensors(float &T, float &RH, uint8_t &aqi, uint16_t &tvoc, uint16_t &eco2) {
  sensors_event_t humidity, temp;
  aht.getEvent(&humidity, &temp);

  T = temp.temperature;
  RH = humidity.relative_humidity;

  // Compensación ENS160
  ens.setTempCompensation(T);
  ens.setRHCompensation(RH);

  aqi = ens.getAQI();
  tvoc = ens.getTVOC();
  eco2 = ens.getECO2();

  // Validación mínima (ajústala si quieres ser estricta)
  // Devuelve false si algo huele raro.
  if (isnan(T) || isnan(RH)) return false;
  if (RH < 0 || RH > 100) return false;
  if (aqi > 5) return false;

  return true;
}

void loop() {
  // Mantener conexiones
  if (WiFi.status() != WL_CONNECTED) {
    wifiConnect();
  }
  if (!mqtt.connected()) {
    mqttConnect();
  }
  mqtt.loop();

  // Envío periódico
  if (millis() - lastSend >= SEND_INTERVAL_MS) {
    lastSend = millis();

    float T, RH;
    uint8_t aqi;
    uint16_t tvoc, eco2;

    bool ok = readSensors(T, RH, aqi, tvoc, eco2);

    // JSON (en el orden pedido)
    StaticJsonDocument<256> doc;
    if (ok) {
      doc["temperatura"] = T;
      doc["humedad"]     = RH;
      doc["aqi"]         = aqi;
      doc["tvoc"]        = tvoc;
      doc["eco2"]        = eco2;
    } else {
      doc["temperatura"] = nullptr;
      doc["humedad"]     = nullptr;
      doc["aqi"]         = nullptr;
      doc["tvoc"]        = nullptr;
      doc["eco2"]        = nullptr;
    }

    char payload[256];
    size_t n = serializeJson(doc, payload, sizeof(payload));

    // Publicar
    bool published = mqtt.publish(MQTT_TOPIC, payload, n);

    // Log local
    Serial.print("MQTT publish ");
    Serial.print(published ? "OK" : "FAIL");
    Serial.print(" -> ");
    Serial.println(payload);
  }
}
