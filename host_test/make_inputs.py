#!/usr/bin/env python3
"""Write the synthetic 96x96 grayscale test inputs as a raw binary file.

usage: make_inputs.py synthetic.bin [--random N]
The first seven images are the inputs of Tables II and III; --random N appends
N random smooth-intensity images (Table V uses N = 50, seed 0).
"""
import argparse
import numpy as np

S = 96

def face(eyes_open):
    yy, xx = np.mgrid[0:S, 0:S]
    img = np.full((S, S), 40, np.uint8)                        # dark background
    img[((xx - 48) / 34) ** 2 + ((yy - 50) / 42) ** 2 <= 1] = 190   # face
    for cx in (32, 64):                                          # eyes
        if eyes_open:
            img[((xx - cx) / 9) ** 2 + ((yy - 40) / 5) ** 2 <= 1] = 250
            img[(xx - cx) ** 2 + (yy - 40) ** 2 <= 9] = 20      # pupil
        else:
            img[(abs(yy - 40) <= 1) & (abs(xx - cx) <= 9)] = 30  # closed lid
    img[(abs(yy - 72) <= 1) & (abs(xx - 48) <= 12)] = 90         # mouth
    return img

def smooth_random(rng):
    small = rng.integers(0, 256, (6, 6)).astype(float)
    # bilinear upsampling of a 6x6 grid to 96x96
    x = np.linspace(0, 5, S)
    i0 = np.floor(x).astype(int).clip(0, 4); t = x - i0
    rows = small[i0] * (1 - t)[:, None] + small[i0 + 1] * t[:, None]
    img = rows[:, i0] * (1 - t)[None, :] + rows[:, i0 + 1] * t[None, :]
    return img.clip(0, 255).astype(np.uint8)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--random", type=int, default=0)
    a = ap.parse_args()
    rng = np.random.default_rng(0)
    imgs = [np.zeros((S, S), np.uint8), np.full((S, S), 255, np.uint8), np.full((S, S), 128, np.uint8),
            np.tile(np.linspace(0, 255, S).astype(np.uint8), (S, 1)),
            rng.integers(0, 256, (S, S)).astype(np.uint8), face(True), face(False)]
    imgs += [smooth_random(rng) for _ in range(a.random)]
    np.stack(imgs).tofile(a.out)
    print(f"wrote {len(imgs)} images to {a.out}")

if __name__ == "__main__":
    main()
