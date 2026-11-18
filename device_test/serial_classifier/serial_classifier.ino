/*
 * Device-side agreement test for the ESP32-CAM
 * --------------------------------------------
 * Receives 96x96 grayscale images (9216 bytes) from a PC over serial,
 * runs the model and returns:
 *   R,<score_fokus>,<score_kantuk>,<classification_time_ms>
 *
 * Upload this sketch once per library variant (V1, V2, V3, V4) and run
 * device_test/send_images.py for each.
 */
#include <klasifikasi_kantuk2_inferencing.h>

#define N_PIXEL (EI_CLASSIFIER_INPUT_WIDTH * EI_CLASSIFIER_INPUT_HEIGHT)

static uint8_t img[N_PIXEL];

// Edge Impulse expects pixels packed as 0xRRGGBB in a float
static int get_data(size_t offset, size_t length, float *out) {
  for (size_t i = 0; i < length; i++) {
    uint8_t g = img[offset + i];
    out[i] = (float)((g << 16) | (g << 8) | g);
  }
  return 0;
}

void setup() {
  Serial.setRxBufferSize(N_PIXEL + 1024);  // must be called before begin()
  Serial.begin(115200);
  Serial.setTimeout(10000);
  delay(1000);
  Serial.printf("READY %dx%d\n", EI_CLASSIFIER_INPUT_WIDTH, EI_CLASSIFIER_INPUT_HEIGHT);
}

void loop() {
  if (!Serial.available()) return;
  if (Serial.read() != 'S') return;   // wait for the start-of-image marker

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
