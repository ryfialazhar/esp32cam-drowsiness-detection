"""
Accuracy and confusion matrix for one result file of send_images.py.
Reproduces Table VI when run on results/device/pilot_V3.csv.

Usage:
    python accuracy.py ../results/device/pilot_V3.csv
"""
import csv, sys

rows = [r for r in csv.DictReader(open(sys.argv[1])) if r["label"]]
classes = ["fokus", "kantuk"]   # fokus = alert, kantuk = drowsy
cm = {a: {b: 0 for b in classes} for a in classes}
for r in rows:
    cm[r["label"]][r["prediksi"]] += 1
n = len(rows)
correct = sum(cm[k][k] for k in classes)
print(f"N = {n}, accuracy = {100*correct/n:.1f}%")
print(f"{'true/predicted':<18}{'fokus':>8}{'kantuk':>8}{'recall':>9}")
for a in classes:
    tot = sum(cm[a].values())
    rec = 100 * cm[a][a] / tot if tot else float("nan")
    print(f"{a:<18}{cm[a]['fokus']:>8}{cm[a]['kantuk']:>8}{rec:>8.1f}%")
