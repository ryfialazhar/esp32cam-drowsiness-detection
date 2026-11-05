"""
Hitung akurasi dan confusion matrix dari satu file hasil kirim_gambar.py.

Pemakaian:
    python akurasi.py pilot.csv
"""
import csv, sys

rows = [r for r in csv.DictReader(open(sys.argv[1])) if r["label"]]
kelas = ["fokus", "kantuk"]
cm = {a: {b: 0 for b in kelas} for a in kelas}
for r in rows:
    cm[r["label"]][r["prediksi"]] += 1
n = len(rows)
benar = sum(cm[k][k] for k in kelas)
print(f"N = {n}, akurasi = {100*benar/n:.1f}%")
print(f"{'label/prediksi':<18}{'fokus':>8}{'kantuk':>8}{'recall':>9}")
for a in kelas:
    tot = sum(cm[a].values())
    rec = 100*cm[a][a]/tot if tot else float('nan')
    print(f"{a:<18}{cm[a]['fokus']:>8}{cm[a]['kantuk']:>8}{rec:>8.1f}%")
