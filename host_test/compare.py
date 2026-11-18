#!/usr/bin/env python3
"""Compare two score CSV files (same inputs, same order) from run_host or the device.

usage: compare.py REFERENCE.csv OTHER.csv
Prints label agreement and the maximum absolute score difference.
"""
import csv, sys

def load(p):
    with open(p) as f:
        r = list(csv.reader(f))
    return r[0][1:], [[float(x) for x in row[1:]] for row in r[1:] if row]

def main():
    labels, a = load(sys.argv[1]); _, b = load(sys.argv[2])
    if len(a) != len(b):
        sys.exit(f"different number of rows: {len(a)} vs {len(b)}")
    same = sum(max(range(len(x)), key=x.__getitem__) == max(range(len(y)), key=y.__getitem__) for x, y in zip(a, b))
    diff = max(abs(p - q) for x, y in zip(a, b) for p, q in zip(x, y))
    print(f"inputs={len(a)} label_agreement={100*same/len(a):.1f}% max_abs_score_diff={diff:.5f}")

if __name__ == "__main__":
    main()
