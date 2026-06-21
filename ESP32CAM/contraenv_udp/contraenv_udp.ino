#include <Wire.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <ESPmDNS.h>
#include <ArduinoJson.h>
#include <Adafruit_AHTX0.h>

// =====================================================
// Contra Espacios - ContraEnv
// ESP32 WROOM / DevKit V1 + ENS160 + AHT2x
// UDP + mDNS + progreso OLED via Node-RED
// ENS160 en deep sleep por I2C entre lecturas
// =====================================================

// -------------------- Identidad --------------------
const char* DEVICE_ID = "contraenv";
const char* MDNS_NAME = "contraenv";   // contraenv.local

// -------------------- WiFi --------------------
const char* WIFI_SSID = "contraespacios";
const char* WIFI_PASS = "cinemabarredura";

// -------------------- LED integrado --------------------
// En muchos ESP32 DevKit V1 es GPIO2.
// Si no ves parpadeo, tu placa puede no tener LED ahí o ser activo en LOW.
#define LED_PIN 2
#define LED_ON HIGH
#define LED_OFF LOW

// -------------------- I2C --------------------
const int I2C_SDA = 21;
const int I2C_SCL = 22;

// -------------------- UDP --------------------
const uint16_t ESP32_UDP_PORT = 4210;     // ESP32 escucha comandos
const uint16_t NODE_RED_UDP_PORT = 5010;  // Node-RED escucha respuestas

// -------------------- Tiempos --------------------
const unsigned long AHT_SETTLE_MS = 1200;
const unsigned long ENS_WARMUP_MS = 20000;
const unsigned long ENS_PROGRESS_INTERVAL_MS = 5000;

const int AHT_DISCARD_READINGS = 2;
const int AHT_AVG_READINGS = 5;
const int ENS_FINAL_READINGS = 3;

// -------------------- Watchdog WiFi --------------------
const unsigned long WIFI_CHECK_INTERVAL_MS = 5000;
const unsigned long WIFI_LOST_RESTART_MS = 30000;

// =====================================================
// ENS160 registros I2C
// =====================================================

const uint8_t ENS160_ADDR_1 = 0x53;
const uint8_t ENS160_ADDR_2 = 0x52;

uint8_t ensAddress = ENS160_ADDR_1;

const uint8_t ENS160_REG_PART_ID   = 0x00;
const uint8_t ENS160_REG_OPMODE    = 0x10;
const uint8_t ENS160_REG_TEMP_IN   = 0x13;
const uint8_t ENS160_REG_RH_IN     = 0x15;
const uint8_t ENS160_REG_STATUS    = 0x20;
const uint8_t ENS160_REG_DATA_AQI  = 0x21;
const uint8_t ENS160_REG_DATA_TVOC = 0x22;
const uint8_t ENS160_REG_DATA_ECO2 = 0x24;

const uint8_t ENS160_MODE_DEEP_SLEEP = 0x00;
const uint8_t ENS160_MODE_IDLE       = 0x01;
const uint8_t ENS160_MODE_STANDARD   = 0x02;
const uint8_t ENS160_MODE_RESET      = 0xF0;

// =====================================================
// Objetos globales
// =====================================================

WiFiUDP udp;
Adafruit_AHTX0 aht;

bool ahtOk = false;
bool ensOk = false;

unsigned long lastWifiCheck = 0;
unsigned long wifiLostSince = 0;

// =====================================================
// Prototipos
// =====================================================

void checkWiFiOrRestart();

// =====================================================
// Estructura lectura
// =====================================================

struct EnvReading {
  bool ok;
  bool aht_ok;
  bool ens_ok;

  float temperature;
  float humidity;

  uint8_t ens_status;
  uint8_t aqi;
  uint16_t tvoc;
  uint16_t eco2;

  String message;
};

// =====================================================
// LED
// =====================================================

void ledOn() {
  digitalWrite(LED_PIN, LED_ON);
}

void ledOff() {
  digitalWrite(LED_PIN, LED_OFF);
}

void blinkSlowOnce() {
  ledOn();
  delay(450);
  ledOff();
  delay(450);
}

void blinkFastOnce() {
  ledOn();
  delay(45);
  ledOff();
  delay(45);
}

void blinkFastTimes(int times) {
  for (int i = 0; i < times; i++) {
    blinkFastOnce();
  }
}

void delayFastBlink(unsigned long durationMs) {
  unsigned long start = millis();

  while (millis() - start < durationMs) {
    blinkFastOnce();
    checkWiFiOrRestart();
  }
}

void solidOnFor(unsigned long durationMs) {
  ledOn();

  unsigned long start = millis();

  while (millis() - start < durationMs) {
    delay(50);
    checkWiFiOrRestart();
  }
}

// =====================================================
// I2C básico
// =====================================================

bool i2cWrite8(uint8_t addr, uint8_t reg, uint8_t value) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

bool i2cWrite16LE(uint8_t addr, uint8_t reg, uint16_t value) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(value & 0xFF);
  Wire.write((value >> 8) & 0xFF);
  return Wire.endTransmission() == 0;
}

bool i2cReadBytes(uint8_t addr, uint8_t reg, uint8_t* buffer, size_t len) {
  Wire.beginTransmission(addr);
  Wire.write(reg);

  if (Wire.endTransmission(false) != 0) {
    return false;
  }

  int received = Wire.requestFrom((int)addr, (int)len);

  if (received != (int)len) {
    return false;
  }

  for (size_t i = 0; i < len; i++) {
    buffer[i] = Wire.read();
  }

  return true;
}

bool i2cRead8(uint8_t addr, uint8_t reg, uint8_t& value) {
  uint8_t buffer[1];

  if (!i2cReadBytes(addr, reg, buffer, 1)) {
    return false;
  }

  value = buffer[0];
  return true;
}

bool i2cRead16LE(uint8_t addr, uint8_t reg, uint16_t& value) {
  uint8_t buffer[2];

  if (!i2cReadBytes(addr, reg, buffer, 2)) {
    return false;
  }

  value = buffer[0] | (buffer[1] << 8);
  return true;
}

void i2cScan() {
  Serial.println("I2C scan:");
  byte count = 0;

  for (byte addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.print("  Encontrado 0x");
      if (addr < 16) Serial.print("0");
      Serial.println(addr, HEX);
      count++;
      delay(2);
    }
  }

  if (count == 0) {
    Serial.println("  No se encontraron dispositivos I2C");
  }
}

// =====================================================
// ENS160
// =====================================================

bool ensSetMode(uint8_t mode) {
  if (!ensOk) return false;

  bool ok = i2cWrite8(ensAddress, ENS160_REG_OPMODE, mode);

  Serial.print("ENS160 mode 0x");
  Serial.print(mode, HEX);
  Serial.print(ok ? " OK" : " ERROR");
  Serial.println();

  return ok;
}

bool ensDeepSleep() {
  bool ok = ensSetMode(ENS160_MODE_DEEP_SLEEP);
  delay(80);
  return ok;
}

bool ensIdle() {
  bool ok = ensSetMode(ENS160_MODE_IDLE);
  delay(80);
  return ok;
}

bool ensStandard() {
  bool ok = ensSetMode(ENS160_MODE_STANDARD);
  delay(120);
  return ok;
}

bool ensReset() {
  bool ok = ensSetMode(ENS160_MODE_RESET);
  delay(100);

  if (!ok) return false;

  ensIdle();
  delay(100);

  return true;
}

bool ensDetectAt(uint8_t addr) {
  uint16_t partId = 0;

  if (!i2cRead16LE(addr, ENS160_REG_PART_ID, partId)) {
    return false;
  }

  Serial.print("ENS160 posible en 0x");
  Serial.print(addr, HEX);
  Serial.print(" PART_ID=0x");
  Serial.println(partId, HEX);

  if (partId == 0x0160) {
    ensAddress = addr;
    return true;
  }

  return false;
}

bool initENS160() {
  ensOk = false;

  if (ensDetectAt(ENS160_ADDR_1)) {
    ensOk = true;
  } else if (ensDetectAt(ENS160_ADDR_2)) {
    ensOk = true;
  }

  if (!ensOk) {
    Serial.println("ERROR: ENS160 no detectado");
    return false;
  }

  Serial.print("ENS160 OK en 0x");
  Serial.println(ensAddress, HEX);

  ensReset();
  ensDeepSleep();

  return true;
}

bool ensSetCompensation(float temperatureC, float humidityRH) {
  if (!ensOk) return false;
  if (isnan(temperatureC) || isnan(humidityRH)) return false;

  if (humidityRH < 0) humidityRH = 0;
  if (humidityRH > 100) humidityRH = 100;

  uint16_t tempRaw = (uint16_t)((temperatureC + 273.15f) * 64.0f);
  uint16_t rhRaw = (uint16_t)(humidityRH * 512.0f);

  bool okT = i2cWrite16LE(ensAddress, ENS160_REG_TEMP_IN, tempRaw);
  bool okH = i2cWrite16LE(ensAddress, ENS160_REG_RH_IN, rhRaw);

  return okT && okH;
}

bool ensReadGas(uint8_t& status, uint8_t& aqi, uint16_t& tvoc, uint16_t& eco2) {
  if (!ensOk) return false;

  bool okStatus = i2cRead8(ensAddress, ENS160_REG_STATUS, status);
  bool okAQI = i2cRead8(ensAddress, ENS160_REG_DATA_AQI, aqi);
  bool okTVOC = i2cRead16LE(ensAddress, ENS160_REG_DATA_TVOC, tvoc);
  bool okECO2 = i2cRead16LE(ensAddress, ENS160_REG_DATA_ECO2, eco2);

  return okStatus && okAQI && okTVOC && okECO2;
}

// =====================================================
// AHT2x
// =====================================================

bool initAHT2x() {
  ahtOk = aht.begin(&Wire);

  if (ahtOk) {
    Serial.println("AHT2x OK");
  } else {
    Serial.println("ERROR: AHT2x no detectado");
  }

  return ahtOk;
}

bool readAHTOnce(float& temperature, float& humidity) {
  if (!ahtOk) return false;

  sensors_event_t humidityEvent;
  sensors_event_t tempEvent;

  aht.getEvent(&humidityEvent, &tempEvent);

  temperature = tempEvent.temperature;
  humidity = humidityEvent.relative_humidity;

  if (isnan(temperature) || isnan(humidity)) return false;
  if (temperature < -20 || temperature > 80) return false;
  if (humidity < 0 || humidity > 100) return false;

  return true;
}

bool readAHTAverage(float& temperature, float& humidity) {
  if (!ahtOk) return false;

  float t = NAN;
  float rh = NAN;

  for (int i = 0; i < AHT_DISCARD_READINGS; i++) {
    readAHTOnce(t, rh);
    delayFastBlink(250);
  }

  float sumT = 0;
  float sumRH = 0;
  int valid = 0;

  for (int i = 0; i < AHT_AVG_READINGS; i++) {
    if (readAHTOnce(t, rh)) {
      sumT += t;
      sumRH += rh;
      valid++;
    }

    delayFastBlink(250);
  }

  if (valid == 0) return false;

  temperature = sumT / valid;
  humidity = sumRH / valid;

  return true;
}

// =====================================================
// WiFi + mDNS
// =====================================================

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.setHostname(DEVICE_ID);
  WiFi.setSleep(false);

  Serial.print("Conectando a WiFi: ");
  Serial.println(WIFI_SSID);

  WiFi.begin(WIFI_SSID, WIFI_PASS);

  unsigned long start = millis();

  while (WiFi.status() != WL_CONNECTED) {
    blinkSlowOnce();
    Serial.print(".");

    if (millis() - start > WIFI_LOST_RESTART_MS) {
      Serial.println();
      Serial.println("WiFi timeout. Reiniciando ESP32...");
      ESP.restart();
    }
  }

  Serial.println();
  Serial.println("WiFi conectado");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
  Serial.print("Hostname DHCP: ");
  Serial.println(WiFi.getHostname());

  solidOnFor(2000);
  ledOff();

  wifiLostSince = 0;
}

void startMDNS() {
  if (MDNS.begin(MDNS_NAME)) {
    MDNS.addService("contraenv", "udp", ESP32_UDP_PORT);

    Serial.print("mDNS iniciado: ");
    Serial.print(MDNS_NAME);
    Serial.println(".local");
  } else {
    Serial.println("ERROR iniciando mDNS");
  }
}

void checkWiFiOrRestart() {
  if (millis() - lastWifiCheck < WIFI_CHECK_INTERVAL_MS) return;

  lastWifiCheck = millis();

  if (WiFi.status() == WL_CONNECTED) {
    wifiLostSince = 0;
    return;
  }

  if (wifiLostSince == 0) {
    wifiLostSince = millis();
    Serial.println("WiFi perdido...");
  }

  if (millis() - wifiLostSince > WIFI_LOST_RESTART_MS) {
    Serial.println("WiFi perdido demasiado tiempo. Reiniciando...");
    ESP.restart();
  }
}

// =====================================================
// UDP JSON
// =====================================================

void sendJsonTo(IPAddress ip, uint16_t port, StaticJsonDocument<768>& doc) {
  char payload[768];
  size_t n = serializeJson(doc, payload, sizeof(payload));

  udp.beginPacket(ip, port);
  udp.write((const uint8_t*)payload, n);
  udp.endPacket();

  Serial.print("UDP -> ");
  Serial.print(ip);
  Serial.print(":");
  Serial.print(port);
  Serial.print(" ");
  Serial.println(payload);
}

void sendProgress(IPAddress ip, const char* stage, const char* message, int progress) {
  StaticJsonDocument<768> doc;

  doc["type"] = "environment";
  doc["device"] = DEVICE_ID;
  doc["hostname"] = "contraenv.local";
  doc["ip"] = WiFi.localIP().toString();
  doc["listen_port"] = ESP32_UDP_PORT;

  doc["state"] = "running";
  doc["stage"] = stage;
  doc["message"] = message;
  doc["progress"] = progress;

  sendJsonTo(ip, NODE_RED_UDP_PORT, doc);
}

void sendEnvironmentFinal(IPAddress ip, EnvReading& r) {
  StaticJsonDocument<768> doc;

  doc["type"] = "environment";
  doc["device"] = DEVICE_ID;
  doc["hostname"] = "contraenv.local";
  doc["ip"] = WiFi.localIP().toString();
  doc["listen_port"] = ESP32_UDP_PORT;

  bool completeOk = r.aht_ok && r.ens_ok;

  doc["state"] = completeOk ? "done" : "error";
  doc["stage"] = "complete";
  doc["message"] = completeOk ? "Ambiente listo" : r.message;
  doc["progress"] = completeOk ? 50 : 35;

  doc["aht_ok"] = r.aht_ok;
  doc["ens_ok"] = r.ens_ok;

  if (r.aht_ok) {
    doc["temperature"] = r.temperature;
    doc["humidity"] = r.humidity;
  } else {
    doc["temperature"] = nullptr;
    doc["humidity"] = nullptr;
  }

  doc["ens_status"] = r.ens_status;

  if (r.ens_ok) {
    doc["aqi"] = r.aqi;
    doc["tvoc"] = r.tvoc;
    doc["eco2"] = r.eco2;
  } else {
    doc["aqi"] = nullptr;
    doc["tvoc"] = nullptr;
    doc["eco2"] = nullptr;
  }

  solidOnFor(5000);
  sendJsonTo(ip, NODE_RED_UDP_PORT, doc);
  blinkFastTimes(10);
  ledOff();
}

// =====================================================
// Inicialización sensores
// =====================================================

void initI2CAndSensors() {
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(400000);

  delay(100);

  i2cScan();

  initAHT2x();
  initENS160();

  if (ensOk) {
    ensDeepSleep();
  }
}

// =====================================================
// Secuencia ambiental
// =====================================================

void readEnvironmentSequence(IPAddress nodeRedIP) {
  EnvReading r;

  r.ok = false;
  r.aht_ok = false;
  r.ens_ok = false;

  r.temperature = NAN;
  r.humidity = NAN;

  r.ens_status = 0;
  r.aqi = 0;
  r.tvoc = 0;
  r.eco2 = 0;

  r.message = "Lectura incompleta";

  Serial.println("Iniciando lectura ambiental completa...");

  sendProgress(nodeRedIP, "start", "Iniciando ambiente", 30);

  if (ensOk) {
    ensDeepSleep();
  }

  sendProgress(nodeRedIP, "aht", "Leyendo temperatura", 35);

  delayFastBlink(AHT_SETTLE_MS);

  float t = NAN;
  float rh = NAN;

  if (readAHTAverage(t, rh)) {
    r.temperature = t;
    r.humidity = rh;
    r.aht_ok = true;
  }

  if (!r.aht_ok) {
    r.message = "Error AHT";
  }

  if (ensOk) {
    sendProgress(nodeRedIP, "ens_start", "Activando gases", 40);

    ensIdle();

    if (r.aht_ok) {
      ensSetCompensation(r.temperature, r.humidity);
    }

    ensStandard();

    unsigned long warmupStart = millis();
    unsigned long lastProgress = 0;

    while (millis() - warmupStart < ENS_WARMUP_MS) {
      unsigned long elapsed = millis() - warmupStart;
      unsigned long remaining = (ENS_WARMUP_MS - elapsed) / 1000;

      if (millis() - lastProgress >= ENS_PROGRESS_INTERVAL_MS) {
        lastProgress = millis();

        int progress = 40 + (int)((elapsed * 8UL) / ENS_WARMUP_MS);
        if (progress > 48) progress = 48;

        char msg[40];
        snprintf(msg, sizeof(msg), "Gases %lus", remaining);

        sendProgress(nodeRedIP, "ens_warmup", msg, progress);
      }

      delayFastBlink(200);
      checkWiFiOrRestart();
    }

    sendProgress(nodeRedIP, "ens_read", "Leyendo gases", 48);

    if (r.aht_ok) {
      ensSetCompensation(r.temperature, r.humidity);
    }

    uint8_t status = 0;
    uint8_t aqi = 0;
    uint16_t tvoc = 0;
    uint16_t eco2 = 0;

    bool gasReadOk = false;

    for (int i = 0; i < ENS_FINAL_READINGS; i++) {
      gasReadOk = ensReadGas(status, aqi, tvoc, eco2);
      delayFastBlink(500);
    }

    r.ens_status = status;
    r.aqi = aqi;
    r.tvoc = tvoc;
    r.eco2 = eco2;

    // TVOC puede ser 0 y seguir siendo válido.
    r.ens_ok = gasReadOk && (r.aqi >= 1 && r.aqi <= 5) && (r.eco2 > 0);

    if (!r.ens_ok) {
      r.message = "ENS no estable";
    }

    ensDeepSleep();
  } else {
    r.message = "ENS no detectado";
  }

  if (r.aht_ok && r.ens_ok) {
    r.ok = true;
    r.message = "Ambiente listo";
  } else {
    r.ok = false;
  }

  sendEnvironmentFinal(nodeRedIP, r);

  Serial.println("Lectura ambiental terminada.");
}

// =====================================================
// UDP receive
// =====================================================

void sendError(IPAddress ip, const char* message) {
  EnvReading r;

  r.ok = false;
  r.aht_ok = false;
  r.ens_ok = false;

  r.temperature = NAN;
  r.humidity = NAN;

  r.ens_status = 0;
  r.aqi = 0;
  r.tvoc = 0;
  r.eco2 = 0;

  r.message = message;

  sendEnvironmentFinal(ip, r);
}

void handleUDPCommand(char* payload, IPAddress senderIP, uint16_t senderPort) {
  Serial.print("UDP <- ");
  Serial.print(senderIP);
  Serial.print(":");
  Serial.print(senderPort);
  Serial.print(" ");
  Serial.println(payload);

  StaticJsonDocument<512> doc;
  DeserializationError error = deserializeJson(doc, payload);

  if (error) {
    sendError(senderIP, "JSON invalido");
    return;
  }

  const char* type = doc["type"] | "";
  const char* command = doc["command"] | "";

  if (strcmp(type, "command") == 0 && strcmp(command, "read_environment") == 0) {
    readEnvironmentSequence(senderIP);
    return;
  }

  if (strcmp(type, "ping") == 0) {
    sendProgress(senderIP, "pong", "ContraEnv online", 0);
    return;
  }

  sendError(senderIP, "Comando no reconocido");
}

void checkUDP() {
  int packetSize = udp.parsePacket();

  if (!packetSize) return;

  char buffer[512];
  int len = udp.read(buffer, sizeof(buffer) - 1);

  if (len <= 0) return;

  buffer[len] = '\0';

  IPAddress senderIP = udp.remoteIP();
  uint16_t senderPort = udp.remotePort();

  handleUDPCommand(buffer, senderIP, senderPort);
}

// =====================================================
// Setup / loop
// =====================================================

void setup() {
  pinMode(LED_PIN, OUTPUT);
  ledOff();

  Serial.begin(115200);
  delay(300);

  Serial.println();
  Serial.println("ContraEnv - ESP32 WROOM + ENS160/AHT2x + UDP");
  Serial.println("Modo: progreso + OK solo si todos los sensores responden");

  connectWiFi();
  startMDNS();

  udp.begin(ESP32_UDP_PORT);

  Serial.print("UDP escuchando en puerto ");
  Serial.println(ESP32_UDP_PORT);

  initI2CAndSensors();

  Serial.println("Nombre local:");
  Serial.println("contraenv.local");

  Serial.println("Comando esperado:");
  Serial.println("{\"type\":\"command\",\"command\":\"read_environment\"}");

  ledOff();

  Serial.println("Listo. Esperando comando UDP...");
}

void loop() {
  checkWiFiOrRestart();
  checkUDP();

  ledOff();

  delay(10);
}