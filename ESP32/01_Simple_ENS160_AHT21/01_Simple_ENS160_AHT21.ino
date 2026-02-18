#include <Wire.h>
#include <Adafruit_AHTX0.h>
#include <SparkFun_ENS160.h>   // SparkFun ENS160 Arduino Library

// --- I2C pins para ESP32 DevKit V1 (cámbialos si usas otros) ---
static const int I2C_SDA = 21;
static const int I2C_SCL = 22;

// --- Objetos ---
Adafruit_AHTX0 aht;
SparkFun_ENS160 ens;

// --- Helper: escáner I2C ---
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

void setup() {
  Serial.begin(115200);
  delay(200);

  // I2C init (ESP32)
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(400000); // 400kHz suele ir bien

  Serial.println("ENS160 + AHT2x Serial Monitor");
  i2cScan();

  // --- AHT2x init ---
  if (!aht.begin(&Wire)) {
    Serial.println("ERROR: No se detecta AHT2x (revisa cableado/direccion).");
    while (1) delay(100);
  }
  Serial.println("AHT2x OK");

  // --- ENS160 init ---
  // Si no sabes la dirección, prueba 0x53 primero (muy común), y si falla prueba 0x52.
  // También puedes ver el i2cScan para confirmar.
  if (!ens.begin(Wire, 0x53)) {
    Serial.println("ENS160 no responde en 0x53, probando 0x52...");
    if (!ens.begin(Wire, 0x52)) {
      Serial.println("ERROR: No se detecta ENS160 (revisa cableado/direccion).");
      while (1) delay(100);
    }
  }
  Serial.println("ENS160 OK");

  // Reset + modo operación estándar
  ens.setOperatingMode(SFE_ENS160_RESET);
  delay(10);
  ens.setOperatingMode(SFE_ENS160_STANDARD);

  // Opcional: imprimir versión / status si la librería lo soporta
  Serial.println("Inicialización completa.\n");
}

void loop() {
  // --- Leer AHT2x ---
  sensors_event_t humidity, temp;
  aht.getEvent(&humidity, &temp);

  float T = temp.temperature;       // °C
  float RH = humidity.relative_humidity; // %

  // --- Compensación en ENS160 (si tu librería lo permite) ---
  // En la SparkFun ENS160, suelen existir métodos para setear temp/hum para compensación.
  // Los nombres exactos pueden variar por versión. Si tu compilación falla aquí,
  // comenta estas líneas y te digo el equivalente para tu versión.
  ens.setTempCompensation(T);
  ens.setRHCompensation(RH);

  // --- Leer ENS160 ---
  // La librería normalmente usa ens.getAQI(), ens.getTVOC(), ens.getECO2()
  // A veces requiere ens.checkDataStatus() o ens.available().
  // Usamos un approach común: pedir valores directo.
  uint8_t aqi = ens.getAQI();
  uint16_t tvoc = ens.getTVOC();    // ppb
  uint16_t eco2 = ens.getECO2();    // ppm

  // --- Imprimir por Serial ---
  Serial.print("T=");
  Serial.print(T, 2);
  Serial.print(" C  RH=");
  Serial.print(RH, 2);
  Serial.print(" %  |  AQI=");
  Serial.print(aqi);
  Serial.print("  TVOC=");
  Serial.print(tvoc);
  Serial.print(" ppb  eCO2=");
  Serial.print(eco2);
  Serial.println(" ppm");

  delay(1000);
}
