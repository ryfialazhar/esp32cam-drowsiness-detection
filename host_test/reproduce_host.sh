#!/usr/bin/env bash
# Reproduces the host-side results of the paper (Tables II, III and V).
# Requirements: Linux or macOS, g++/gcc, python3 with numpy, unzip.
# Run from the repository root:  bash host_test/reproduce_host.sh
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
T="$ROOT/host_test"; B="$T/.work"; OUT="$ROOT/results/host"
mkdir -p "$B" "$OUT"
unz() { rm -rf "$B/$2"; mkdir -p "$B/$2"; unzip -q "$ROOT/lib/$1" -d "$B/$2"; echo "$B/$2/klasifikasi_kantuk2_inferencing"; }

python3 "$T/make_inputs.py" "$B/synthetic57.bin" --random 50
head -c $((7*9216)) "$B/synthetic57.bin" > "$B/synthetic7.bin"

echo "== Deployed model (MobileNetV2 0.35, Studio 1.93.6): Tables II and III"
V1=$(unz V1_original_mobilenetv2_0.35.zip v1)
python3 "$T/make_variant.py" "$V1" "$B/v4" --variant V4 >/dev/null
python3 "$T/build.py" "$V1" "$B/deployed_reference"
python3 "$T/build.py" "$V1" "$B/deployed_espnn" --esp-nn
for op in conv depthwise_conv add softmax fully_connected; do
  python3 "$T/build.py" "$V1" "$B/deployed_espnn_ref_$op" --esp-nn --ref-op "$op"
done
python3 "$T/build.py" "$B/v4" "$B/deployed_espnn_V4" --esp-nn
for b in reference espnn espnn_V4 espnn_ref_conv espnn_ref_depthwise_conv espnn_ref_add espnn_ref_softmax espnn_ref_fully_connected; do
  "$B/deployed_$b" "$B/synthetic7.bin" 2>/dev/null > "$OUT/deployed_$b.csv"
done

echo "== Other models (Studio 1.97.3): Table V"
for m in mobilenetv1_0.25 mobilenetv2_0.1; do
  L=$(unz "${m}_studio1.97.3.zip" "$m")
  python3 "$T/make_variant.py" "$L" "$B/${m}_orig" --variant original >/dev/null
  python3 "$T/build.py" "$L" "$B/${m}_reference"
  python3 "$T/build.py" "$L" "$B/${m}_espnn_shipped" --esp-nn
  python3 "$T/build.py" "$B/${m}_orig" "$B/${m}_espnn_original_lines" --esp-nn
  for b in reference espnn_shipped espnn_original_lines; do
    "$B/${m}_$b" "$B/synthetic57.bin" 2>/dev/null > "$OUT/${m}_$b.csv"
  done
done
"$B/deployed_reference" "$B/synthetic57.bin" 2>/dev/null > "$OUT/deployed_reference_57.csv"
"$B/deployed_espnn" "$B/synthetic57.bin" 2>/dev/null > "$OUT/deployed_espnn_57.csv"
"$B/deployed_espnn_V4" "$B/synthetic57.bin" 2>/dev/null > "$OUT/deployed_espnn_V4_57.csv"

{
  echo "Host differential test, $(date -u +%Y-%m-%d)"
  echo; echo "Tables II/III: deployed model, 7 synthetic inputs, compared with the reference build"
  for b in espnn espnn_ref_conv espnn_ref_depthwise_conv espnn_ref_add espnn_ref_softmax espnn_ref_fully_connected espnn_V4; do
    printf "%-32s %s\n" "$b" "$(python3 "$T/compare.py" "$OUT/deployed_reference.csv" "$OUT/deployed_$b.csv")"
  done
  echo; echo "Table V: 57 inputs (7 synthetic + 50 random smooth images), compared with each model's reference build"
  printf "%-44s %s\n" "mobilenetv2_0.35 (deployed) original lines" "$(python3 "$T/compare.py" "$OUT/deployed_reference_57.csv" "$OUT/deployed_espnn_57.csv")"
  printf "%-44s %s\n" "mobilenetv2_0.35 (deployed) fixed lines" "$(python3 "$T/compare.py" "$OUT/deployed_reference_57.csv" "$OUT/deployed_espnn_V4_57.csv")"
  for m in mobilenetv1_0.25 mobilenetv2_0.1; do
    printf "%-44s %s\n" "$m original lines" "$(python3 "$T/compare.py" "$OUT/${m}_reference.csv" "$OUT/${m}_espnn_original_lines.csv")"
    printf "%-44s %s\n" "$m shipped (fixed) lines" "$(python3 "$T/compare.py" "$OUT/${m}_reference.csv" "$OUT/${m}_espnn_shipped.csv")"
  done
} | tee "$OUT/summary.txt"
