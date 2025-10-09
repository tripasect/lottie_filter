import json, sys
import colorsys
import argparse
from dataclasses import dataclass

# ==============================
# 🎚️  RUNTIME CONFIG (from flags)
# ==============================
@dataclass
class Config:
    contrast: float = 1.0      # 1 = neutral
    brightness: float = 0.0    # additive offset, recommended [-1..1]
    saturation: float = 1.0    # 0 = grayscale, 1 = original
    hue_deg: float = 0.0       # degrees to rotate hue (0 = no shift)
# ==============================


def lerp(a, b, t): 
    return a + (b - a) * t


def adjust_color_triplet(r, g, b, cfg: Config):
    # --- Hue Shift ---
    if cfg.hue_deg:
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        h = (h + (cfg.hue_deg / 360.0)) % 1.0
        r, g, b = colorsys.hsv_to_rgb(h, s, v)

    # --- Saturation ---
    gray = 0.299*r + 0.587*g + 0.114*b
    r = lerp(gray, r, cfg.saturation)
    g = lerp(gray, g, cfg.saturation)
    b = lerp(gray, b, cfg.saturation)

    # --- Contrast ---
    def contrast_fn(x):
        return max(0, min(1, 0.5 + cfg.contrast * (x - 0.5)))
    r, g, b = contrast_fn(r), contrast_fn(g), contrast_fn(b)

    # --- Brightness ---
    r, g, b = [max(0, min(1, c + cfg.brightness)) for c in (r, g, b)]

    return r, g, b


def adjust_rgba(color, cfg: Config):
    if not isinstance(color, list) or len(color) < 3:
        return color
    r, g, b = color[:3]
    a = color[3] if len(color) > 3 else 1
    r, g, b = adjust_color_triplet(r, g, b, cfg)
    return [r, g, b, a]


def adjust_gradient(gradient, cfg: Config):
    arr = gradient.get("k")
    if not isinstance(arr, list):
        return
    # The structure is [offset, r, g, b, offset, r, g, b, ...]
    for i in range(0, len(arr)-3, 4):
        r, g, b = arr[i+1:i+4]
        r, g, b = adjust_color_triplet(r, g, b, cfg)
        arr[i+1:i+4] = [r, g, b]


def recurse(obj, cfg: Config):
    if isinstance(obj, dict):
        for key, val in obj.items():
            # Solid fill / stroke / line colors
            if key in ("c", "fc", "sc", "lc") and isinstance(val, dict):
                k = val.get("k")
                if isinstance(k, list) and len(k) >= 3:
                    val["k"] = adjust_rgba(k, cfg)
                elif isinstance(k, list) and len(k) > 0 and isinstance(k[0], dict):
                    for f in k:
                        if "s" in f: f["s"] = adjust_rgba(f["s"], cfg)
                        if "e" in f: f["e"] = adjust_rgba(f["e"], cfg)
            # Gradient fill
            elif key == "g" and isinstance(val, dict):
                k = val.get("k")
                if isinstance(k, dict) and isinstance(k.get("k"), list):
                    adjust_gradient(k, cfg)
            else:
                recurse(val, cfg)
    elif isinstance(obj, list):
        for v in obj:
            recurse(v, cfg)


def main():
    parser = argparse.ArgumentParser(
        description="Apply contrast, brightness, saturation, and hue shift to Lottie colors"
    )
    parser.add_argument("input", help="Input Lottie JSON file")
    parser.add_argument("output", help="Output JSON file")
    parser.add_argument("--contrast", type=float, default=1.0, help="Contrast multiplier (1 = neutral)")
    parser.add_argument("--brightness", type=float, default=0.0, help="Brightness offset added to channels [-1..1] recommended")
    parser.add_argument("--saturation", type=float, default=1.0, help="Saturation blend factor (0 = grayscale, 1 = original)")
    parser.add_argument("--hue-deg", type=float, default=0.0, help="Hue shift in degrees (0 = no shift)")

    args = parser.parse_args()

    cfg = Config(
        contrast=args.contrast,
        brightness=args.brightness,
        saturation=args.saturation,
        hue_deg=args.hue_deg,
    )

    with open(args.input, "r") as f:
        data = json.load(f)
    recurse(data, cfg)
    with open(args.output, "w") as f:
        json.dump(data, f, indent=2)
    print(
        f"✅ Saved processed file to {args.output} (contrast={cfg.contrast}, brightness={cfg.brightness}, saturation={cfg.saturation}, hue_deg={cfg.hue_deg})"
    )


if __name__ == "__main__":
    main()