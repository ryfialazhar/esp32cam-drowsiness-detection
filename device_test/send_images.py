"""
Stream test images to the ESP32-CAM running serial_classifier.ino and save the
predictions to CSV.

Usage:
    pip install pyserial pillow
    python send_images.py --port COM3 --folder test_images --out V1.csv

The true label is taken from the file name:
  * MRL Eye Dataset names, e.g. s0001_00664_0_0_0_0_0_01.png: the 5th field is
    the eye state (0 = closed -> kantuk/drowsy, 1 = open -> fokus/alert);
  * frames saved by firmware/capture_frames: fokus.<time>.jpg / kantuk.<time>.jpg.
Output columns: file, label, fokus, kantuk, prediksi (predicted label), ms
(classification time reported by the Edge Impulse SDK on the device).
The model's class names are Indonesian: fokus = alert, kantuk = drowsy.
"""
import argparse, csv, os, sys, time
import serial
from PIL import Image

SIZE = 96
EXT = (".png", ".jpg", ".jpeg", ".bmp")


def label_from_name(name):
    base = os.path.basename(name).lower()
    for lb in ("fokus", "kantuk"):
        if base.startswith(lb + "."):
            return lb
    parts = os.path.splitext(os.path.basename(name))[0].split("_")
    # files exported from Edge Impulse may start with "label." -> drop it
    if "." in parts[0]:
        parts[0] = parts[0].split(".")[-1]
    if len(parts) >= 5 and parts[4] in ("0", "1"):
        return "fokus" if parts[4] == "1" else "kantuk"
    return ""


def prepare(path):
    """Grayscale, centre crop to a square ('fit shortest axis'), resize to 96x96."""
    im = Image.open(path).convert("L")
    w, h = im.size
    s = min(w, h)
    left, top = (w - s) // 2, (h - s) // 2
    im = im.crop((left, top, left + s, top + s)).resize((SIZE, SIZE), Image.BILINEAR)
    return im.tobytes()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True)
    ap.add_argument("--folder", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--baud", type=int, default=115200)
    a = ap.parse_args()

    files = sorted(os.path.join(r, f) for r, _, fs in os.walk(a.folder) for f in fs if f.lower().endswith(EXT))
    if not files:
        sys.exit("No images found in " + a.folder)
    print(f"{len(files)} images found")

    # keep DTR/RTS low so that the ESP32-CAM (e.g. on an ESP32-CAM-MB board) is not held in reset
    ser = serial.Serial()
    ser.port, ser.baudrate, ser.timeout = a.port, a.baud, 30
    ser.dtr = False
    ser.rts = False
    try:
        ser.open()
    except serial.SerialException as e:
        sys.exit(f"Cannot open {a.port}: {e}\nClose the Arduino Serial Monitor and try again.")
    ser.timeout = 1
    start = time.time()
    while time.time() - start < 8:          # wait for READY from the device
        line = ser.readline().decode(errors="ignore").strip()
        if line.startswith("READY"):
            print("Device ready:", line)
            break
    ser.timeout = 30
    ser.reset_input_buffer()

    with open(a.out, "w", newline="") as fo:
        wr = csv.writer(fo)
        wr.writerow(["file", "label", "fokus", "kantuk", "prediksi", "ms"])
        for i, p in enumerate(files, 1):
            ser.write(b"S" + prepare(p))
            ser.flush()
            line, start = "", time.time()
            while time.time() - start < 60:
                line = ser.readline().decode(errors="ignore").strip()
                if line.startswith(("R,", "ERR")):
                    break
            if not line.startswith("R,"):
                print(f"[{i}] {os.path.basename(p)}: failed ({line})")
                continue
            _, fk, kt, ms = line.split(",")
            pred = "fokus" if float(fk) >= float(kt) else "kantuk"
            wr.writerow([os.path.basename(p), label_from_name(p), fk, kt, pred, ms])
            print(f"[{i}/{len(files)}] {os.path.basename(p)} -> {pred} ({fk}/{kt}) {ms} ms")
    ser.close()
    print("Done. Results saved to", a.out)


if __name__ == "__main__":
    main()
