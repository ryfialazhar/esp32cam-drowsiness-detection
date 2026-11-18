"""
Compare device results of library variants against the reference variant
(V2, ESP-NN disabled). Reproduces Table IV.

Usage:
    python compare_variants.py ../results/device/V1.csv ../results/device/V3.csv ../results/device/V4.csv --ref ../results/device/V2.csv
"""
import argparse, csv


def read(path):
    with open(path) as f:
        return {r["file"]: r for r in csv.DictReader(f)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="+")
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()

    ref = read(a.ref)
    print(f"{'variant':<28}{'N':>5}{'accuracy':>10}{'same label as ref':>19}{'mean |diff|':>13}{'max |diff|':>12}{'mean ms':>10}")
    for path in a.csv + [a.ref]:
        d = read(path)
        names = [k for k in d if k in ref]
        n = len(names)
        if n == 0:
            print(path, ": no file names in common with the reference")
            continue
        labelled = [k for k in names if d[k]["label"]]
        correct = sum(1 for k in labelled if d[k]["prediksi"] == d[k]["label"])
        same = sum(1 for k in names if d[k]["prediksi"] == ref[k]["prediksi"])
        diff = [abs(float(d[k]["kantuk"]) - float(ref[k]["kantuk"])) for k in names]
        ms = sum(float(d[k]["ms"]) for k in names) / n
        acc = 100 * correct / len(labelled) if labelled else float("nan")
        print(f"{path[-28:]:<28}{n:>5}{acc:>9.1f}%{100*same/n:>18.1f}%{sum(diff)/n:>13.4f}{max(diff):>12.4f}{ms:>10.0f}")


if __name__ == "__main__":
    main()
