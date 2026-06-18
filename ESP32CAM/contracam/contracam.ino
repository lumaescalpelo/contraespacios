#include <Arduino.h>
#include "esp_camera.h"
#include <WiFi.h>
#include <ESPmDNS.h>

// ===========================
// Select camera model in board_config.h
// ===========================
#include "board_config.h"

// ===========================
// Enter your WiFi credentials
// ===========================
// Para desarrollo rápido puedes poner el hotspot del teléfono con estos datos.
// Si usas otra red, cambia ssid/password y conserva el hostname.
const char *ssid = "contraespacios";
const char *password = "cinemabarredura";

// ===========================
// Contra Espacios network config
// ===========================
const char *hostName = "contracam";

// Reinicia si la ESP32CAM pierde WiFi durante demasiado tiempo.
// Esto evita dejar la cámara colgada en instalación o durante pruebas móviles.
const unsigned long WIFI_CHECK_INTERVAL_MS = 5000;
const unsigned long WIFI_LOST_RESTART_MS = 30000;

unsigned long lastWifiCheck = 0;
unsigned long wifiLostSince = 0;

void startCameraServer();
void setupLedFlash();
void connectWiFi();
void startMDNS();
void checkWiFiOrRestart();

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.frame_size = FRAMESIZE_VGA;  // ContraCam: arranque en 640x480
  config.pixel_format = PIXFORMAT_JPEG;  // for streaming
  //config.pixel_format = PIXFORMAT_RGB565; // for face detection/recognition
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12;
  config.fb_count = 1;

  // if PSRAM IC present, init with UXGA resolution and higher JPEG quality
  //                      for larger pre-allocated frame buffer.
  if (config.pixel_format == PIXFORMAT_JPEG) {
    if (psramFound()) {
      config.jpeg_quality = 10;
      config.fb_count = 2;
      config.grab_mode = CAMERA_GRAB_LATEST;
    } else {
      // Limit the frame size when PSRAM is not available
      config.frame_size = FRAMESIZE_VGA;
      config.fb_location = CAMERA_FB_IN_DRAM;
    }
  } else {
    // Best option for face detection/recognition
    config.frame_size = FRAMESIZE_240X240;
#if CONFIG_IDF_TARGET_ESP32S3
    config.fb_count = 2;
#endif
  }

#if defined(CAMERA_MODEL_ESP_EYE)
  pinMode(13, INPUT_PULLUP);
  pinMode(14, INPUT_PULLUP);
#endif

  // camera init
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  sensor_t *s = esp_camera_sensor_get();
  // initial sensors are flipped vertically and colors are a bit saturated
  if (s->id.PID == OV3660_PID) {
    s->set_vflip(s, 1);        // flip it back
    s->set_brightness(s, 1);   // up the brightness just a bit
    s->set_saturation(s, -2);  // lower the saturation
  }
  // ContraCam: mantener resolución inicial en VGA 640x480.
  // El ejemplo original baja a QVGA; aquí lo dejamos en VGA para captura útil.
  if (config.pixel_format == PIXFORMAT_JPEG) {
    s->set_framesize(s, FRAMESIZE_VGA);
  }

#if defined(CAMERA_MODEL_M5STACK_WIDE) || defined(CAMERA_MODEL_M5STACK_ESP32CAM)
  s->set_vflip(s, 1);
  s->set_hmirror(s, 1);
#endif

#if defined(CAMERA_MODEL_ESP32S3_EYE)
  s->set_vflip(s, 1);
#endif

// Setup LED FLash if LED pin is defined in camera_pins.h
#if defined(LED_GPIO_NUM)
  setupLedFlash();
#endif

  connectWiFi();
  startMDNS();

  startCameraServer();

  Serial.println("");
  Serial.println("Camera Ready!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
  Serial.print("Hostname DHCP: ");
  Serial.println(WiFi.getHostname());
  Serial.println("mDNS URL: http://contracam.local");
  Serial.println("Capture:  http://contracam.local/capture");
  Serial.println("Stream:   http://contracam.local:81/stream");
}

void loop() {
  checkWiFiOrRestart();
  delay(100);
}

void connectWiFi() {
  WiFi.mode(WIFI_STA);

  // El hostname debe establecerse antes de WiFi.begin().
  WiFi.setHostname(hostName);

  // Reduce problemas de latencia/desconexión en uso como cámara.
  WiFi.setSleep(false);

  Serial.print("Connecting to WiFi SSID: ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  unsigned long startedAt = millis();

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");

    if (millis() - startedAt > WIFI_LOST_RESTART_MS) {
      Serial.println("");
      Serial.println("WiFi connection timeout. Restarting ESP32CAM...");
      ESP.restart();
    }
  }

  Serial.println("");
  Serial.println("WiFi connected");
  wifiLostSince = 0;
}

void startMDNS() {
  if (MDNS.begin(hostName)) {
    MDNS.addService("http", "tcp", 80);
    MDNS.addService("mjpeg", "tcp", 81);
    Serial.print("mDNS responder started: http://");
    Serial.print(hostName);
    Serial.println(".local");
  } else {
    Serial.println("Error starting mDNS responder");
  }
}

void checkWiFiOrRestart() {
  if (millis() - lastWifiCheck < WIFI_CHECK_INTERVAL_MS) {
    return;
  }

  lastWifiCheck = millis();

  if (WiFi.status() == WL_CONNECTED) {
    wifiLostSince = 0;
    return;
  }

  if (wifiLostSince == 0) {
    wifiLostSince = millis();
    Serial.println("WiFi lost. Waiting before restart...");
  }

  if (millis() - wifiLostSince > WIFI_LOST_RESTART_MS) {
    Serial.println("WiFi lost for too long. Restarting ESP32CAM...");
    ESP.restart();
  }
}
