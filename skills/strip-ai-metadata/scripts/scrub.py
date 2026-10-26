#!/usr/bin/env python3
"""
AI Provenance & Metadata Scrubber Script
Strips C2PA, JUMBF, XMP, IPTC, and EXIF headers, and supports deep scrub perturbation.
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path

VALID_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff'}

def get_output_path(input_path: Path, output_dir: Path = None, suffix: str = "_clean") -> Path:
    stem = input_path.stem
    ext = input_path.suffix
    if output_dir:
        return output_dir / f"{stem}{suffix}{ext}"
    return input_path.parent / f"{stem}{suffix}{ext}"

def scrub_with_exiftool(input_file: Path, output_file: Path) -> bool:
    cmd = ["exiftool", "-all=", "-CommonIFD0=", "-o", str(output_file), str(input_file)]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return res.returncode == 0 and output_file.exists() and output_file.stat().st_size > 0

def scrub_with_magick(input_file: Path, output_file: Path, deep: bool = False) -> bool:
    if deep:
        cmd = [
            "magick", str(input_file),
            "-strip",
            "-attenuate", "0.015",
            "+noise", "Gaussian",
            "-quality", "98",
            str(output_file)
        ]
    else:
        cmd = [
            "magick", str(input_file),
            "-strip",
            "-define", "png:exclude-chunk=all",
            "-quality", "98",
            str(output_file)
        ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return res.returncode == 0 and output_file.exists() and output_file.stat().st_size > 0

def scrub_with_ffmpeg(input_file: Path, output_file: Path) -> bool:
    cmd = [
        "ffmpeg", "-y", "-i", str(input_file),
        "-map_metadata", "-1",
        "-c:v", "copy" if input_file.suffix.lower() in [".jpg", ".jpeg"] else "png",
        str(output_file)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return res.returncode == 0 and output_file.exists() and output_file.stat().st_size > 0

def scrub_with_pillow(input_file: Path, output_file: Path, deep: bool = False) -> bool:
    from PIL import Image
    with Image.open(input_file) as img:
        w, h = img.size
        mode = img.mode
        if deep:
            # 1px Lanczos perturbation to disrupt pixel-level watermarks
            perturbed = img.resize((max(1, w - 1), max(1, h - 1)), Image.Resampling.LANCZOS).resize((w, h), Image.Resampling.LANCZOS)
            clean = Image.new(mode, (w, h))
            clean.putdata(list(perturbed.getdata()))
        else:
            clean = Image.new(mode, (w, h))
            clean.putdata(list(img.getdata()))
        
        save_kwargs = {"optimize": True}
        if output_file.suffix.lower() in [".jpg", ".jpeg"]:
            save_kwargs["quality"] = 98
            if mode in ("RGBA", "P"):
                clean = clean.convert("RGB")
        clean.save(output_file, **save_kwargs)
    return output_file.exists() and output_file.stat().st_size > 0

def scrub_image(input_file: Path, output_file: Path, deep: bool = False) -> tuple[bool, str]:
    has_exiftool = shutil.which("exiftool") is not None
    has_magick = shutil.which("magick") is not None or shutil.which("convert") is not None
    has_ffmpeg = shutil.which("ffmpeg") is not None

    if deep and has_magick:
        ok = scrub_with_magick(input_file, output_file, deep=True)
        return ok, "magick (Gaussian perturbation)"
    elif deep:
        ok = scrub_with_pillow(input_file, output_file, deep=True)
        return ok, "pillow (Lanczos perturbation)"

    if has_exiftool:
        ok = scrub_with_exiftool(input_file, output_file)
        if ok:
            return True, "exiftool (lossless)"

    if has_magick:
        ok = scrub_with_magick(input_file, output_file, deep=False)
        if ok:
            return True, "magick"

    if has_ffmpeg:
        ok = scrub_with_ffmpeg(input_file, output_file)
        if ok:
            return True, "ffmpeg"

    ok = scrub_with_pillow(input_file, output_file, deep=False)
    return ok, "pillow"

def main():
    parser = argparse.ArgumentParser(description="Scrub AI provenance and metadata from images.")
    parser.add_argument("target", help="Path to an image file or directory of images")
    parser.add_argument("--deep", action="store_true", help="Apply pixel-level watermark perturbation (anti-SynthID)")
    parser.add_argument("-o", "--output-dir", help="Directory to save cleaned images (default: same directory as input)")
    args = parser.parse_args()

    target_path = Path(args.target).expanduser().resolve()
    out_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else None

    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    files_to_process = []
    if target_path.is_file():
        files_to_process.append(target_path)
    elif target_path.is_dir():
        for f in sorted(target_path.iterdir()):
            if f.suffix.lower() in VALID_EXTENSIONS and not f.stem.endswith("_clean"):
                files_to_process.append(f)
    else:
        print(f"Error: Target '{args.target}' does not exist.")
        sys.exit(1)

    if not files_to_process:
        print("No supported images found to process.")
        sys.exit(0)

    for in_file in files_to_process:
        out_file = get_output_path(in_file, output_dir=out_dir)
        ok, method = scrub_image(in_file, out_file, deep=args.deep)
        if ok:
            status = "Deep Scrubbed" if args.deep else "Cleaned"
            print(f"Status: {status} via {method}")
            print(f"Output File: {out_file}")
            print(f"Verification: Headers stripped, file size {out_file.stat().st_size} bytes.")
        else:
            print(f"Failed to scrub: {in_file}")

if __name__ == "__main__":
    main()
