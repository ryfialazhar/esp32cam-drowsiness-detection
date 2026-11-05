"""
Bandingkan hasil tiga varian library terhadap varian referensi (V2, tanpa ESP-NN).

Pemakaian:
    python bandingkan.py V1.csv V2.csv V3.csv --ref V2.csv
"""
import argparse, csv


def baca(path):
    with open(path) as f:
        return {r["file"]: r for r in csv.DictReader(f)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="+")
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()

    ref = baca(a.ref)
    print(f"{'Varian':<10}{'N':>5}{'Akurasi':>10}{'Sama label ref':>16}{'Selisih skor rata2':>20}{'Selisih maks':>14}{'Waktu rata2 (ms)':>18}")
    for path in a.csv:
        d = baca(path)
        nama = [k for k in d if k in ref]
        n = len(nama)
        if n == 0:
            print(path, ": tidak ada file yang cocok dengan referensi")
            continue
        benar = sum(1 for k in nama if d[k]["label"] and d[k]["prediksi"] == d[k]["label"])
        berlabel = sum(1 for k in nama if d[k]["label"])
        sama = sum(1 for k in nama if d[k]["prediksi"] == ref[k]["prediksi"])
        selisih = [abs(float(d[k]["kantuk"]) - float(ref[k]["kantuk"])) for k in nama]
        waktu = sum(float(d[k]["ms"]) for k in nama) / n
        akurasi = 100 * benar / berlabel if berlabel else float("nan")
        print(f"{path:<10}{n:>5}{akurasi:>9.1f}%{100*sama/n:>15.1f}%{sum(selisih)/n:>20.4f}{max(selisih):>14.4f}{waktu:>18.0f}")


if __name__ == "__main__":
    main()
