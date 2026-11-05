"""
Kirim gambar uji MRL ke ESP32-CAM dan simpan hasil prediksinya ke CSV.

Pemakaian:
    pip install pyserial pillow
    python kirim_gambar.py --port COM3 --folder data_uji --out V1.csv

Label diambil dari nama file MRL: kolom ke-5 = status mata
(0 = tertutup -> kantuk, 1 = terbuka -> fokus).
Contoh: s0001_00664_0_0_0_0_0_01.png -> kantuk
"""
import argparse, csv, os, sys, time
import serial
from PIL import Image

SIZE = 96
EXT = (".png", ".jpg", ".jpeg", ".bmp")


def label_dari_nama(nama):
    dasar = os.path.basename(nama).lower()
    # Foto dari sketch pengambil data: fokus.<waktu>.jpg / kantuk.<waktu>.jpg
    for lb in ("fokus", "kantuk"):
        if dasar.startswith(lb + "."):
            return lb
    bagian = os.path.splitext(os.path.basename(nama))[0].split("_")
    # Nama hasil ekspor Edge Impulse kadang diawali "label." -> buang
    if "." in bagian[0]:
        bagian[0] = bagian[0].split(".")[-1]
    if len(bagian) >= 5 and bagian[4] in ("0", "1"):
        return "fokus" if bagian[4] == "1" else "kantuk"
    return ""


def siapkan(path):
    """Grayscale + 'fit shortest axis' (potong tengah jadi persegi) + resize 96x96."""
    im = Image.open(path).convert("L")
    w, h = im.size
    s = min(w, h)
    kiri, atas = (w - s) // 2, (h - s) // 2
    im = im.crop((kiri, atas, kiri + s, atas + s)).resize((SIZE, SIZE), Image.BILINEAR)
    return im.tobytes()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True)
    ap.add_argument("--folder", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--baud", type=int, default=115200)
    a = ap.parse_args()

    files = sorted(
        os.path.join(r, f)
        for r, _, fs in os.walk(a.folder) for f in fs if f.lower().endswith(EXT)
    )
    if not files:
        sys.exit("Tidak ada gambar di folder " + a.folder)
    print(f"{len(files)} gambar ditemukan")

    # DTR/RTS dimatikan supaya ESP32-CAM (mis. papan ESP32-CAM-MB) tidak tertahan reset
    ser = serial.Serial()
    ser.port, ser.baudrate, ser.timeout = a.port, a.baud, 30
    ser.dtr = False
    ser.rts = False
    try:
        ser.open()
    except serial.SerialException as e:
        sys.exit(f"Port {a.port} tidak bisa dibuka: {e}\n"
                 "Tutup Serial Monitor / Arduino IDE, lalu coba lagi.")
    # tunggu pesan READY dari ESP32 (maks 8 detik)
    ser.timeout = 1
    mulai = time.time()
    while time.time() - mulai < 8:
        baris = ser.readline().decode(errors="ignore").strip()
        if baris.startswith("READY"):
            print("ESP32 siap:", baris)
            break
    ser.timeout = 30
    ser.reset_input_buffer()

    with open(a.out, "w", newline="") as fo:
        wr = csv.writer(fo)
        wr.writerow(["file", "label", "fokus", "kantuk", "prediksi", "ms"])
        for i, p in enumerate(files, 1):
            ser.write(b"S" + siapkan(p))
            ser.flush()
            baris = ""
            mulai = time.time()
            while time.time() - mulai < 60:
                baris = ser.readline().decode(errors="ignore").strip()
                if baris.startswith(("R,", "ERR")):
                    break
            if not baris.startswith("R,"):
                print(f"[{i}] {os.path.basename(p)}: gagal ({baris})")
                continue
            _, fk, kt, ms = baris.split(",")
            pred = "fokus" if float(fk) >= float(kt) else "kantuk"
            wr.writerow([os.path.basename(p), label_dari_nama(p), fk, kt, pred, ms])
            print(f"[{i}/{len(files)}] {os.path.basename(p)} -> {pred} ({fk}/{kt}) {ms} ms")
    ser.close()
    print("Selesai. Hasil disimpan di", a.out)


if __name__ == "__main__":
    main()
