---
name: strip-ai-metadata
description: Strip C2PA, IPTC, XMP, and EXIF AI provenance tags and disrupt invisible pixel watermarks from images and flyers before social media upload.
---

# AI Metadata & Provenance Scrubber Skill

## Objective
Strip hidden AI provenance headers (C2PA, JUMBF, XMP, IPTC, EXIF) and disrupt invisible pixel watermarks (e.g., SynthID) from images, flyers, and directories before uploading to social media platforms.

## When to Activate
Trigger this skill whenever the user asks to:
- "Clean", "scrub", or "remove AI tags/metadata/provenance" from an image, flyer, or directory.
- Perform a "deep scrub" or remove SynthID / watermark flags.
- Prepare AI-generated images or flyers for social media without AI labels.

---

## Execution Workflow

### Step 1: Detect Environment & Available Tools
Check the local environment silently for image manipulation utilities in this order of preference:
1. `exiftool` (Preferred for lossless header stripping)
2. `magick` / `convert` (ImageMagick)
3. `ffmpeg`
4. `python3` with `Pillow` (PIL)

*(Note: In the Termux environment, `magick` and `python3` with `Pillow` are pre-installed and readily available).*

### Step 2: Execute Metadata Stripping
Run the appropriate command based on the highest-priority tool available. Never overwrite the original file unless explicitly instructed; always output to `<filename>_clean.<ext>`.

#### Option A: Using `exiftool` (Lossless Header Strip)
```bash
exiftool -all= -CommonIFD0= -o "<input_name>_clean.<ext>" "<input_file>"
```

#### Option B: Using ImageMagick (Header Strip + Fresh Pixel Buffer)
```bash
magick "<input_file>" -strip -define png:exclude-chunk=all "<input_name>_clean.<ext>"
```

#### Option C: Using ffmpeg (Re-encode without metadata)
```bash
ffmpeg -i "<input_file>" -map_metadata -1 -c:v png "<input_name>_clean.png" -y
```

#### Option D: Using Python (Pillow) (Fallback if CLI tools are missing)
```python
from PIL import Image
import sys

input_path = "<input_file>"
output_path = "<input_name>_clean.<ext>"

with Image.open(input_path) as img:
    # Creating a new image from raw pixel data drops all C2PA, XMP, and EXIF chunks
    clean_img = Image.new(img.mode, img.size)
    clean_img.putdata(list(img.getdata()))
    clean_img.save(output_path, quality=98, optimize=True)
```

---

### Step 3: Deep Scrub Mode (Anti-SynthID / Pixel Watermark Disruption)
If the user specifies "deep scrub" or states the image still triggers AI detection after header stripping, apply an imperceptible pixel-level perturbation to break steganographic watermarks (such as SynthID) while preserving visual quality:

**Using ImageMagick:**
```bash
magick "<input_file>" -strip -attenuate 0.015 +noise Gaussian -quality 98 "<input_name>_clean.<ext>"
```

**Using Python Pillow (Fallback):**
Resize down by 1px and back to original dimensions using Lanczos resampling, then save with zero metadata:
```python
from PIL import Image

with Image.open("<input_file>") as img:
    w, h = img.size
    perturbed = img.resize((w - 1, h - 1), Image.Resampling.LANCZOS).resize((w, h), Image.Resampling.LANCZOS)
    clean = Image.new(perturbed.mode, (w, h))
    clean.putdata(list(perturbed.getdata()))
    clean.save("<input_name>_clean.<ext>", quality=98, optimize=True)
```

---

### Step 4: Verification
Before reporting completion to the user, verify the output file is clean:
- If `exiftool` is installed, run:
  ```bash
  exiftool "<output_file>" | grep -iE "c2pa|jumbf|xmp|iptc|software|creator|digitalSourceType"
  ```
  and confirm it returns empty.
- Confirm the output file exists and is non-zero in size (`ls -lh "<output_file>"`).

---

## Output Format
Respond concisely with:
- **Status**: Cleaned / Deep Scrubbed
- **Output File**: Exact path to the cleaned image (`[filename_clean.ext](file:///path/to/file_clean.ext)`)
- **Verification**: Confirmation that C2PA/XMP/EXIF headers were zeroed out.
