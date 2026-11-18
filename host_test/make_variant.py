#!/usr/bin/env python3
"""Create the library variants used in the paper from an Edge Impulse Arduino library.

usage: make_variant.py SRC_LIBRARY DST_LIBRARY --variant {V2,V3,V4,original}

V2        ESP-NN disabled for every operator (reference kernels only)
V3        ESP-NN enabled except for the fully connected operator
V4        ESP-NN enabled; the two shape lines of the ESP-NN fully connected
          branch replaced by the general form (the fix proposed in the paper)
original  the inverse of V4: put the original two lines back into a library
          exported with a newer SDK that already contains the general form
          (used for Table V)

V1 is the unmodified library as exported by Edge Impulse Studio 1.93.6.
"""
import argparse, re, shutil
from pathlib import Path

ORIG = ("      const int batches = output_shape.Dims(0);\n"
        "      const int output_depth = output_shape.Dims(1);\n")
FIXED = ("      // general form: supports outputs with more than two dimensions (keep_num_dims = true)\n"
         "      const int output_dim_count = output_shape.DimensionsCount();\n"
         "      const int batches = FlatSizeSkipDim(output_shape, output_dim_count - 1);\n"
         "      const int output_depth = output_shape.Dims(output_dim_count - 1);\n")
SHAPE = re.compile(r"(#if ESP_NN\n(?:.*\n){0,3}?\s*const int filter_dim_count = filter_shape\.DimensionsCount\(\);\n)"
                   r"((?:\s*//[^\n]*\n)?(?:\s*const int output_dim_count = output_shape\.DimensionsCount\(\);\n)?"
                   r"\s*const int batches = [^\n]*\n\s*const int output_depth = [^\n]*\n)")

def one_sub(pattern, repl, text, what):
    new, n = re.subn(pattern, repl, text)
    if n != 1:
        raise SystemExit(f"{what}: expected exactly one match, found {n}")
    return new

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("--variant", required=True, choices=["V2", "V3", "V4", "original"])
    a = ap.parse_args()
    dst = Path(a.dst)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(a.src, dst)
    fc = next(dst.rglob("tensorflow/lite/micro/kernels/fully_connected.cpp"))
    cfg = next(dst.rglob("edge-impulse-sdk/classifier/ei_classifier_config.h"))
    if a.variant == "V2":
        t = cfg.read_text()
        t = one_sub(r'(#include "sdkconfig.h"\n)(\s*)#define EI_CLASSIFIER_TFLITE_ENABLE_ESP_NN\s+1\n',
                    r'\1\2// V2: ESP-NN disabled for all operators (reference kernels only)\n'
                    r'\2#define EI_CLASSIFIER_TFLITE_ENABLE_ESP_NN      0\n', t, "ESP-NN switch")
        cfg.write_text(t)
    elif a.variant == "V3":
        t = fc.read_text()
        t = one_sub(r"#elif EI_CLASSIFIER_TFLITE_ENABLE_ESP_NN == 1\n",
                    "// V3: the ESP-NN fully connected kernel returns wrong results for this model,\n"
                    "// so this layer uses the reference kernel; all other layers keep ESP-NN.\n"
                    "#elif 0 && (EI_CLASSIFIER_TFLITE_ENABLE_ESP_NN == 1)\n", t, "ESP-NN FC branch")
        fc.write_text(t)
    else:
        t = fc.read_text()
        t = one_sub(SHAPE, lambda m: m.group(1) + (FIXED if a.variant == "V4" else ORIG), t, "ESP-NN FC shape lines")
        fc.write_text(t)
    print(f"{dst}: variant {a.variant}")

if __name__ == "__main__":
    main()
