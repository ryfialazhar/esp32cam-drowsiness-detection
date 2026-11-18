# Device results (ESP32-CAM, Arduino ESP32 core 2.0.17)

One CSV per run of `device_test/send_images.py`, one row per image:
`file, label, fokus, kantuk, prediksi, ms` (fokus = alert score, kantuk = drowsy score,
prediksi = predicted label, ms = classification time reported by the SDK).

| File | Library | Images | Paper |
|---|---|---|---|
| `V1.csv` | V1, original (ESP-NN) | 239 MRL test images | Table IV |
| `V2.csv` | V2, ESP-NN disabled (reference) | 239 MRL test images | Table IV |
| `V3.csv` | V3, ESP-NN except fully connected | 239 MRL test images | Table IV |
| `V4.csv` | V4, ESP-NN with the two-line fix | 239 MRL test images | Table IV |
| `pilot_V3.csv` | V3 | 382 ESP32-CAM frames | Table VI |

Reproduce the tables:
```
python device_test/compare_variants.py results/device/V1.csv results/device/V3.csv results/device/V4.csv --ref results/device/V2.csv
python device_test/accuracy.py results/device/pilot_V3.csv
```
