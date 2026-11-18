// Reads N raw 96x96 8-bit grayscale images from a binary file and prints the
// class scores of the compiled Edge Impulse model as CSV on stdout.
// Usage: ./run_host images.bin > scores.csv
#include <cstdio>
#include <vector>
#include "edge-impulse-sdk/classifier/ei_run_classifier.h"

static const uint8_t *g_img;
static int get_data(size_t offset, size_t length, float *out) {
  for (size_t i = 0; i < length; i++) {
    uint32_t g = g_img[offset + i];
    out[i] = (float)((g << 16) | (g << 8) | g);  // packed RGB, as the camera example does
  }
  return 0;
}

int main(int argc, char **argv) {
  if (argc < 2) { fprintf(stderr, "usage: %s images.bin\n", argv[0]); return 1; }
  FILE *f = fopen(argv[1], "rb");
  if (!f) { perror(argv[1]); return 1; }
  const size_t n_px = EI_CLASSIFIER_INPUT_WIDTH * EI_CLASSIFIER_INPUT_HEIGHT;
  std::vector<uint8_t> img(n_px);
  printf("index");
  for (size_t c = 0; c < EI_CLASSIFIER_LABEL_COUNT; c++) printf(",%s", ei_classifier_inferencing_categories[c]);
  printf("\n");
  for (int idx = 0; fread(img.data(), 1, n_px, f) == n_px; idx++) {
    g_img = img.data();
    signal_t sig; sig.total_length = n_px; sig.get_data = &get_data;
    ei_impulse_result_t r = {0};
    if (run_classifier(&sig, &r, false) != EI_IMPULSE_OK) { fprintf(stderr, "run_classifier failed\n"); return 1; }
    printf("%d", idx);
    for (size_t c = 0; c < EI_CLASSIFIER_LABEL_COUNT; c++) printf(",%.5f", r.classification[c].value);
    printf("\n");
  }
  fclose(f);
  return 0;
}
