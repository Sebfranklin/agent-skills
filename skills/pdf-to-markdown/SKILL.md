---
name: pdf-to-markdown
description: Converts PDF documents, books, and forms into clean, structured Markdown (.md) files 100% locally on-device. Zero token ingestion and zero LLM context window bloat. Automatically extracts bookmark outlines into Markdown headings, restores Unicode ligatures, de-hyphenates line wraps, and formats paragraphs.
---

# PDF to Markdown Converter Skill

## Overview
A fast, lightweight, and offline PDF-to-Markdown processing pipeline that runs entirely on-device without ingesting raw document text into the AI context window. It extracts clean Markdown with proper heading hierarchies, cleaned-up typography, restored ligatures, and reflowed paragraphs.

---

## When to Activate
Trigger this skill whenever the user asks to:
- "Convert this PDF to Markdown / .md"
- "Turn these downloaded PDFs into md files directly"
- "Extract PDF text to markdown without context bloat / token waste"
- "Batch convert PDFs in a directory to clean markdown"

---

## Core Principles
1. **Zero Context Bloat**: Never read, dump, or `cat` long extracted book texts into tool outputs or prompt context. Run the converter script directly on-device and output only stats (page count, word count, file size, destination path).
2. **Offline & Local**: 100% on-device processing via Python (`pypdf`), zero cloud API dependencies, zero mobile data usage.
3. **Structure Preservation**:
   - Preserves PDF table of contents / bookmarks, translating them directly into Markdown headings (`#`, `##`, `###`).
   - Resolves typographer's ligatures (`fi`, `fl`, `ff`, `ffi`, `ffl`).
   - De-hyphenates broken words across wrapped lines.
   - Merges wrapped lines into natural paragraphs while respecting dialogue and section breaks.

---

## Tooling & Path Reference
- **Script Location**: `~/.agents/skills/pdf-to-markdown/scripts/pdf_to_md.py`
- **Environment**: Python 3 with `pypdf` (installed via `pip install pypdf`).

---

## Usage Commands

### 1. Convert a Single PDF
```bash
python3 ~/.agents/skills/pdf-to-markdown/scripts/pdf_to_md.py "/path/to/document.pdf"
```
*(By default, outputs `document.md` in the same directory as the PDF)*

### 2. Convert with Explicit Output Path
```bash
python3 ~/.agents/skills/pdf-to-markdown/scripts/pdf_to_md.py "/path/to/document.pdf" -o "/path/to/output.md"
```

### 3. Batch Convert Multiple PDFs to a Target Directory
```bash
python3 ~/.agents/skills/pdf-to-markdown/scripts/pdf_to_md.py \
  "/storage/emulated/0/Download/book1.pdf" \
  "/storage/emulated/0/Download/book2.pdf" \
  -d "/storage/emulated/0/Download/"
```

### 4. Convert All PDFs in a Directory
```bash
python3 ~/.agents/skills/pdf-to-markdown/scripts/pdf_to_md.py /storage/emulated/0/Download/*.pdf -d /storage/emulated/0/Download/
```

---

## Output Verification
When reporting back to the user:
- Report the **Total Pages**, **Word Count**, and **File Size**.
- Provide a clickable markdown link to the generated `.md` file using the `file://` scheme (e.g., `[document.md](file:///path/to/document.md)`).
- Never dump full book contents into the chat.
