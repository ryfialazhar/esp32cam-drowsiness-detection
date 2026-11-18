#!/usr/bin/env python3
"""Build an Edge Impulse Arduino library as a host executable.

usage: build.py LIBRARY_DIR OUTPUT_EXE [--esp-nn] [--ref-op conv,depthwise_conv,...]

LIBRARY_DIR  the unzipped Edge Impulse Arduino library (the folder that contains src/)
--esp-nn     compile with ESP-NN enabled (generic C kernels, as on the original ESP32)
--ref-op     with --esp-nn, compile these kernel files with ESP-NN disabled
             (operator ablation); names are kernel file stems, e.g. fully_connected
Object files are cached per library and per flag set in .build/.
"""
import argparse, hashlib, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKIP_DIRS = ("porting/arduino", "porting/particle", "porting/espressif/esp-dsp", "porting/espressif/debug_log",
             "CMSIS", "third_party/arc_mli", "/esp32s3", "/esp32p4", "porting/espressif/ESP-NN/test",
             "porting/espressif/ESP-NN/tests")

def sources(src):
    for p in sorted(src.rglob("*")):
        if p.suffix not in (".c", ".cc", ".cpp") or not p.is_file():
            continue
        rel = p.relative_to(src).as_posix()
        if any(s in "/" + rel for s in SKIP_DIRS):
            continue
        if "ESP-NN" in rel and ("esp32s3" in rel or "esp32p4" in rel or rel.endswith(".S")):
            continue
        yield p

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lib"); ap.add_argument("out")
    ap.add_argument("--esp-nn", action="store_true")
    ap.add_argument("--ref-op", default="")
    a = ap.parse_args()
    src = Path(a.lib).resolve() / "src"
    ref_ops = {x.strip() for x in a.ref_op.split(",") if x.strip()}
    nn = src / "edge-impulse-sdk/porting/espressif/ESP-NN"
    inc = [src, src / "edge-impulse-sdk", src / "edge-impulse-sdk/third_party/flatbuffers/include",
           src / "edge-impulse-sdk/third_party/gemmlowp", src / "edge-impulse-sdk/third_party/ruy",
           nn / "include", nn / "src/common", HERE / "stubs"]
    base = ["-O2", "-w", "-DEI_PORTING_POSIX=1", "-DEI_PORTING_ARDUINO=0", "-DTF_LITE_STATIC_MEMORY",
            "-DEI_CLASSIFIER_TFLITE_ENABLE_CMSIS_NN=0"] + [f"-I{p}" for p in inc]
    key = hashlib.md5(str(src).encode()).hexdigest()[:8]
    objdir = HERE / ".build" / key
    files = list(sources(src)) + [HERE / "porting_posix.cpp", HERE / "run_host.cpp"]

    def job(p):
        espnn = a.esp_nn and not (p.stem in ref_ops and "micro/kernels" in p.as_posix())
        flags = base + [f"-DEI_CLASSIFIER_TFLITE_ENABLE_ESP_NN={1 if espnn else 0}"]
        if espnn:
            flags += ["-DESP_NN=1"]
        tag = "nn" if espnn else "ref"
        o = objdir / tag / (hashlib.md5(str(p).encode()).hexdigest()[:10] + "_" + p.stem + ".o")
        if not o.exists() or o.stat().st_mtime < p.stat().st_mtime:
            o.parent.mkdir(parents=True, exist_ok=True)
            cc = ["gcc", "-std=gnu11"] if p.suffix == ".c" else ["g++", "-std=gnu++17"]
            r = subprocess.run(cc + flags + ["-c", str(p), "-o", str(o)], capture_output=True, text=True)
            if r.returncode:
                sys.exit(f"compile failed: {p}\n{r.stderr[-3000:]}")
        return str(o)

    with ThreadPoolExecutor(os.cpu_count() or 4) as ex:
        objs = list(ex.map(job, files))
    subprocess.run(["g++", "-o", a.out] + objs + ["-lm", "-lpthread"], check=True)
    print("built", a.out, "esp-nn" if a.esp_nn else "reference", ("ref-op=" + ",".join(sorted(ref_ops))) if ref_ops else "")

if __name__ == "__main__":
    main()
