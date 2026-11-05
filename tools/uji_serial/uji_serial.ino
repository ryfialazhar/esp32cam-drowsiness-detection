/*
 * Uji kesesuaian prediksi di ESP32-CAM
 * ------------------------------------
 * Menerima gambar 96x96 grayscale (9216 byte) dari PC lewat Serial,
 * menjalankan model, lalu mengirim balik hasilnya:
 *   R,<skor_fokus>,<skor_kantuk>,<waktu_klasifikasi_ms>
 *
 * Upload sketch ini 3 kali, masing-masing dengan varian library:
 *   V1 = library asli (ESP-NN aktif)
 *   V2 = library tanpa ESP-NN
 *   V3 = library perbaikan (ESP-NN kecuali fully connected)
 */
#include <klasifikasi_kantuk2_inferencing.h>

#define N_PIXEL (EI_CLASSIFIER_INPUT_WIDTH * EI_CLASSIFIER_INPUT_HEIGHT)

static uint8_t img[N_PIXEL];

// Edge Impulse mengharapkan piksel dikemas sebagai 0xRRGGBB dalam float
static int get_data(size_t offset, size_t length, float *out) {
  for (size_t i = 0; i < length; i++) {
    uint8_t g = img[offset + i];
    out[i] = (float)((g << 16) | (g << 8) | g);
  }
  return 0;
}

void setup() {
  Serial.setRxBufferSize(N_PIXEL + 1024);  // harus sebelum begin()
  Serial.begin(115200);
  Serial.setTimeout(10000);
  delay(1000);
  Serial.printf("READY %dx%d\n", EI_CLASSIFIER_INPUT_WIDTH, EI_CLASSIFIER_INPUT_HEIGHT);
}

void loop() {
  if (!Serial.available()) return;
  if (Serial.read() != 'S') return;   // tunggu penanda awal gambar

  size_t got = Serial.readBytes(img, N_PIXEL);
  if (got != N_PIXEL) {
    Serial.printf("ERR,%u\n", (unsigned)got);
    return;
  }

  ei::signal_t signal;
  signal.total_length = N_PIXEL;
  signal.get_data = &get_data;

  ei_impulse_result_t result = {0};
  EI_IMPULSE_ERROR err = run_classifier(&signal, &result, false);
  if (err != EI_IMPULSE_OK) {
    Serial.printf("ERR,run_classifier %d\n", err);
    return;
  }

  float fokus = 0, kantuk = 0;
  for (uint16_t i = 0; i < EI_CLASSIFIER_LABEL_COUNT; i++) {
    if (strcmp(ei_classifier_inferencing_categories[i], "fokus") == 0)  fokus  = result.classification[i].value;
    if (strcmp(ei_classifier_inferencing_categories[i], "kantuk") == 0) kantuk = result.classification[i].value;
  }
  Serial.printf("R,%.5f,%.5f,%d\n", fokus, kantuk, result.timing.classification);
}
