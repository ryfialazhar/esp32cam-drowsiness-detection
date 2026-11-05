# ESP32-CAM Drowsiness Detection (TinyML)

On-device drowsiness detection on a low-cost **ESP32-CAM (AI Thinker)**. The device runs a quantized image classifier built with **Edge Impulse** and sounds a buzzer when the user stays drowsy for longer than a set time. All inference runs on the microcontroller, so no cloud or internet connection is needed.

This repository also documents a numerical bug in the ESP-NN optimized *fully connected* kernel and gives a fix that keeps ESP-NN speed while restoring correct predictions.

## Hardware

| Component | Notes |
|---|---|
| ESP32-CAM AI Thinker (OV2640, 4 MB PSRAM) | Main board |
| Active buzzer | GPIO 14 |
| USB-to-serial adapter (FTDI / CH340) | For flashing and Serial Monitor |

## Model

| Item | Value |
|---|---|
| Platform | Edge Impulse Studio |
| Input | 96 × 96 grayscale, resize mode *fit shortest axis* |
| Architecture | MobileNetV2 96×96 0.35 (transfer learning, 16-neuron final layer) |
| Classes | `fokus` (alert), `kantuk` (drowsy) |
| Deployment | Arduino library, int8 quantized, EON compiled |
| Training data | Public eye-state dataset from Kaggle (close-up eye crops) |
| Validation accuracy (int8) | 93.3% |
| Test accuracy (float32) | 95.4% |

## Alarm logic

The model is an **image classifier**, so the sketch reads `result.classification[]` rather than object-detection bounding boxes. The buzzer turns on only when the `kantuk` score stays at or above `KANTUK_THRESHOLD` (default 0.70) for `KANTUK_DURATION_MS` (default 1500 ms). It turns off as soon as the score drops below the threshold.

## Finding: ESP-NN *fully connected* kernel bug

With the original Edge Impulse library (exported with Studio 1.93.6), the ESP32-CAM returned **exactly the same prediction for every frame** (`fokus: 0.99609`), even with the lens fully covered. The same model behaved correctly in Edge Impulse Studio.

**Diagnosis**

1. A brightness check on the captured frames confirmed that the camera delivered changing images.
2. The library was compiled and run on a PC with the TFLite Micro reference kernels: predictions were correct.
3. Rebuilding on the PC with ESP-NN's generic C kernels (the ones used on the original ESP32) reproduced the constant output.
4. Disabling ESP-NN one operator at a time showed that only the **fully connected** kernel was wrong.

**Root cause**

The ESP-NN branch of `fully_connected.cpp` takes the output depth from the *second* dimension of the output tensor. The model has a 16-neuron dense layer with `keep_num_dims = true`, so its output is 4-D (1 × 1 × 1 × 16): the second dimension is 1 and only the first neuron is computed. Newer Edge Impulse SDK releases (e.g. Studio 1.97.3) already contain the general form; libraries exported earlier are still affected.

**Fix (V4, recommended)** in `src/edge-impulse-sdk/tensorflow/lite/micro/kernels/fully_connected.cpp`, ESP-NN branch:

```cpp
// before
const int batches = output_shape.Dims(0);
const int output_depth = output_shape.Dims(1);
// after
const int output_dim_count = output_shape.DimensionsCount();
const int batches = FlatSizeSkipDim(output_shape, output_dim_count - 1);
const int output_depth = output_shape.Dims(output_dim_count - 1);
```

**Results on the ESP32-CAM** (239 MRL test images, Arduino ESP32 core 2.0.17)

| Library variant | Time per image | Accuracy | Labels equal to reference |
|---|---|---|---|
| V1: ESP-NN, original | 1.071 s | 49.8% | 40.2% |
| V2: ESP-NN disabled (reference) | 8.146 s | 90.4% | 100% |
| V3: ESP-NN except fully connected | 1.097 s | 90.4% | 100% |
| **V4: ESP-NN with two-line fix** | **1.095 s** | **90.4%** | **100%** |

## Repository structure

```
esp32cam-drowsiness-detection/
├── code4_fixed/
│   └── code4_fixed.ino                          # Main sketch
├── lib/
│   └── klasifikasi_kantuk2_inferencing.zip      # Edge Impulse library with the V4 fix
├── tools/
│   ├── uji_serial/uji_serial.ino                # streams test images to the device over serial
│   ├── kirim_gambar.py                          # sends images, logs predictions to CSV
│   ├── bandingkan.py                            # compares library variants against the reference
│   └── akurasi.py                               # accuracy and confusion matrix
└── README.md
```

## How to run

1. Install **Arduino IDE 2.x** and the **ESP32 board package by Espressif, version 2.0.17**.
2. Add the library: *Sketch → Include Library → Add .ZIP Library* and select the zip in `lib/`.
3. Select **Tools → Board → AI Thinker ESP32-CAM**, set **PSRAM: Enabled** and **CPU Frequency: 240 MHz**.
4. Open `code4_fixed.ino`, then compile and upload.
5. Open the Serial Monitor at **115200 baud** to see the predictions and the alarm status.

If the build fails with a linker error after you change the library, delete the Arduino build cache (`%LOCALAPPDATA%\arduino\sketches` on Windows) and compile again.

## Limitations and next steps

- The training data are close-up near-infrared eye crops, while the ESP32-CAM captures full-face frames. On 382 frames captured with the device, accuracy dropped to 30.6%, so the model must be retrained on device data before practical use.
- **Next step:** collect training images directly with the ESP32-CAM in its real mounting position, then retrain. A lighter backbone such as MobileNetV1 0.25 will also be tested to reduce latency further.

## Author

**Ryfial Azhar**, Department of Informatics Engineering, Universitas Tadulako, Indonesia
Google Scholar: https://scholar.google.com/citations?user=XY3_FR8AAAAJ

## License

The sketch is based on the Edge Impulse ESP32 camera example (MIT License). The Edge Impulse SDK and the TensorFlow Lite Micro components keep their original licenses (Apache 2.0 / MIT).
