# ESP32-CAM Drowsiness Detection (TinyML) and the ESP-NN Fully Connected Kernel Fault

On-device drowsiness detection on a low-cost **ESP32-CAM (AI Thinker)** with an int8 image classifier built in **Edge Impulse**, and the materials that reproduce the results of the paper

> *Diagnosing a Silent ESP-NN Fully Connected Kernel Failure in TinyML* (manuscript under review, Journal of Edge Computing).

With the original Edge Impulse library (Studio 1.93.6) the ESP32-CAM returned the same prediction for every frame (`fokus: 0.99609`). The cause is the ESP-NN branch of the fully connected kernel, which reads the output depth from the wrong tensor dimension when a dense layer keeps a four-dimensional output (`keep_num_dims = true`). A two-line fix keeps ESP-NN speed and restores outputs identical to the reference kernels.

```cpp
// src/edge-impulse-sdk/tensorflow/lite/micro/kernels/fully_connected.cpp, ESP-NN branch
// before
const int batches = output_shape.Dims(0);
const int output_depth = output_shape.Dims(1);
// after (V4)
const int output_dim_count = output_shape.DimensionsCount();
const int batches = FlatSizeSkipDim(output_shape, output_dim_count - 1);
const int output_depth = output_shape.Dims(output_dim_count - 1);
```

## Where each result in the paper comes from

| Paper | What | How to reproduce | Stored result |
|---|---|---|---|
| Table I | Edge Impulse metrics of the model | Edge Impulse Studio project (reported values) | – |
| Tables II, III | Host differential test and operator ablation | `bash host_test/reproduce_host.sh` | `results/host/deployed_*.csv`, `results/host/summary.txt` |
| Table IV, Fig. 3 | Library variants V1–V4 on the ESP32-CAM, 239 MRL test images | `device_test/` (needs the device) | `results/device/V1.csv` … `V4.csv` |
| Table V | Original vs. fixed lines on three models (host) | `bash host_test/reproduce_host.sh` | `results/host/mobilenet*.csv`, `results/host/summary.txt` |
| Table VI | Pilot on 382 ESP32-CAM frames | `device_test/accuracy.py` | `results/device/pilot_V3.csv` |

## Repository structure

```
├── firmware/
│   ├── drowsiness_detector/      main sketch: camera, classifier, buzzer alarm (GPIO 14)
│   └── capture_frames/           Wi-Fi frame collector used for the pilot images
├── lib/
│   ├── V1_original_mobilenetv2_0.35.zip    deployed model, library as exported (Studio 1.93.6)
│   ├── V4_fixed_mobilenetv2_0.35.zip       same library with the two-line fix (recommended)
│   ├── mobilenetv1_0.25_studio1.97.3.zip   additional model for Table V
│   └── mobilenetv2_0.1_studio1.97.3.zip    additional model for Table V
├── host_test/                    differential testing on a PC (Linux/macOS)
│   ├── build.py                  builds a library as a host executable, reference or ESP-NN kernels,
│   │                             with optional per-operator ablation (--ref-op)
│   ├── porting_posix.cpp         minimal POSIX porting layer for the Edge Impulse SDK
│   ├── run_host.cpp              runs raw 96x96 images through the model, prints scores as CSV
│   ├── make_inputs.py            synthetic inputs (7 for Tables II–III, +50 random for Table V)
│   ├── make_variant.py           creates library variants V2, V3, V4 (and "original" for Table V)
│   ├── compare.py                label agreement and max score difference between two runs
│   ├── stubs/esp_timer.h         host stub for an ESP-IDF header
│   └── reproduce_host.sh         runs everything above
├── device_test/                  agreement test on the ESP32-CAM
│   ├── serial_classifier/        sketch: receives an image over serial, returns scores and time
│   ├── send_images.py            streams a folder of images to the device, writes a CSV
│   ├── compare_variants.py       Table IV from the device CSVs
│   └── accuracy.py               accuracy and confusion matrix (Table VI)
├── results/
│   ├── host/                     outputs of reproduce_host.sh
│   └── device/                   per-image outputs recorded on the ESP32-CAM
└── data/README.md                dataset access and the test split
```

## Reproduce the host results (no hardware needed)

Requirements: Linux or macOS, `g++`/`gcc` (tested with GCC 13.3), Python 3 with `numpy`, `unzip`.

```bash
bash host_test/reproduce_host.sh      # about 10 minutes on 2 cores
cat results/host/summary.txt
```

The script builds each library for the PC with the TFLite Micro reference kernels and with ESP-NN enabled. Without an ESP32-S3 or ESP32-P4 target defined, ESP-NN selects its generic C kernels, which are the kernels used on the original ESP32. Expected output:

```
Tables II/III: deployed model, 7 synthetic inputs, compared with the reference build
espnn                            label_agreement=42.9%  max_abs_score_diff=0.90625   (stuck at fokus 0.99609)
espnn_ref_conv / _depthwise_conv / _add / _softmax      same as espnn
espnn_ref_fully_connected        label_agreement=100.0% max_abs_score_diff=0.00000
espnn_V4                         label_agreement=100.0% max_abs_score_diff=0.00000
Table V: 57 inputs
mobilenetv1_0.25 original lines  label_agreement=100.0% (no dense layer, not affected)
mobilenetv2_0.1  original lines  label_agreement=93.0%  max_abs_score_diff=0.74609
all fixed/shipped lines          label_agreement=100.0% max_abs_score_diff=0.00000
```

## Reproduce the device results

Hardware: AI Thinker ESP32-CAM (4 MB PSRAM), USB-to-serial adapter. Software: Arduino IDE 2.x, **ESP32 Arduino core 2.0.17**, Python 3 with `pyserial` and `pillow`.

1. Create the variant libraries from `lib/V1_original_mobilenetv2_0.35.zip` with `host_test/make_variant.py` (V2, V3, V4) and zip each folder, or use the V1 and V4 zips directly.
2. *Sketch → Include Library → Add .ZIP Library*, select the variant. Board: *AI Thinker ESP32-CAM*, PSRAM enabled, 240 MHz.
3. Upload `device_test/serial_classifier/serial_classifier.ino`.
4. `python device_test/send_images.py --port COM3 --folder <test images> --out V1.csv`
5. Repeat for each variant, then `python device_test/compare_variants.py V1.csv V3.csv V4.csv --ref V2.csv`.

If the build fails with a linker error after you change the library, delete the Arduino build cache (`%LOCALAPPDATA%\arduino\sketches` on Windows) and compile again.

## Run the detector

Add `lib/V4_fixed_mobilenetv2_0.35.zip` as a library, open `firmware/drowsiness_detector/drowsiness_detector.ino`, select *AI Thinker ESP32-CAM*, PSRAM enabled, and upload. The buzzer turns on when the drowsy score stays at or above 0.70 for 1.5 s. The model's class names are Indonesian: `fokus` = alert, `kantuk` = drowsy.

**Limitation.** The model was trained on near-infrared eye crops of one MRL subject; on 382 full-face frames captured with the device it reached only 30.6% accuracy (Table VI). Retrain on device data before practical use.

## Licence

Code written for this project (`firmware/`, `host_test/`, `device_test/`) is released under the MIT Licence (see `LICENSE`). The main sketch is based on the Edge Impulse ESP32 camera example (MIT). The Edge Impulse SDK, TensorFlow Lite Micro and ESP-NN inside `lib/` keep their own licences (Apache 2.0 / BSD / MIT), included in each library. The MRL Eye Dataset is not redistributed here; see `data/README.md`.
