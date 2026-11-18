# Data

## MRL Eye Dataset (training and test images)

The classifier was trained and tested on images of a single subject (`s0001`) of the public
**MRL Eye Dataset** (R. Fusek, "Pupil localization using geodesic distance", ISVC 2018,
doi:10.1007/978-3-030-03801-4_38), available from the MRL website (http://mrl.cs.vsb.cz/eyedataset).
The images are not redistributed in this repository.

* 1,200 images in total: 961 for training (481 open, 480 closed) and 239 for testing
  (119 open, 120 closed); Edge Impulse held out 20% of the training set for validation.
* The 239 test images are listed in `data/test_files.txt` (original MRL file names).
  In the result files the names carry a suffix added by Edge Impulse on import
  (e.g. `s0001_00004_0_0_0_0_0_01.png.6qhm49st.ingestion-....jpg`); the part up to
  `.png` is the MRL name. In MRL names the fifth field is the eye state
  (`1` = open = `fokus`/alert, `0` = closed = `kantuk`/drowsy).
* Preprocessing on the PC (`device_test/send_images.py`): grayscale, centre crop to a
  square, bilinear resize to 96 × 96.

## Pilot frames (Table VI)

382 frames (203 eyes open, 179 eyes closed) of the first author's face were captured with
the ESP32-CAM at about 40 cm (QVGA JPEG) using `firmware/capture_frames`. Because they show
an identifiable face, the images are not published. The per-frame predictions and labels are in
`results/device/pilot_V3.csv`.

## Synthetic inputs (Tables II, III and V)

Generated deterministically by `host_test/make_inputs.py` (seed 0).
