#!/usr/bin/env python3
"""
pdf_to_md.py - High-fidelity, local, offline PDF to Markdown converter.
Zero context bloat: streams and converts PDFs directly on-device without model token ingestion.
Preserves outline hierarchy, fixes ligatures, handles hyphenation, and reflows paragraphs.
"""

import sys
import os
import argparse
import re
from typing import List, Tuple, Dict, Any

try:
    import pypdf
except ImportError:
    print("Error: 'pypdf' is required. Install it using: pip install pypdf", file=sys.stderr)
    sys.exit(1)


LIGATURE_MAP = {
    '\ufb00': 'ff',
    '\ufb01': 'fi',
    '\ufb02': 'fl',
    '\ufb03': 'ffi',
    '\ufb04': 'ffl',
    '\ufb05': 'ft',
    '\ufb06': 'st',
    'ﬁ': 'fi',
    'ﬂ': 'fl',
    'ﬀ': 'ff',
    'ﬃ': 'ffi',
    'ﬄ': 'ffl',
    '\xa0': ' ',
    '\u200b': '',   # zero-width space
    '\u200e': '',   # LTR mark
    '\u200f': '',   # RTL mark
}


def clean_text(text: str) -> str:
    """Replaces Unicode ligatures and normalizes whitespace artifacts."""
    if not text:
        return ""
    for k, v in LIGATURE_MAP.items():
        if k in text:
            text = text.replace(k, v)
    return text


def extract_outline(reader: pypdf.PdfReader) -> Dict[int, List[Tuple[int, str]]]:
    """Extracts PDF bookmarks/outline mapped to 0-indexed page numbers."""
    outline_map: Dict[int, List[Tuple[int, str]]] = {}
    
    def _walk(outline, level=1):
        for item in outline:
            if isinstance(item, list):
                _walk(item, level + 1)
            else:
                try:
                    p = reader.get_destination_page_number(item)
                    if p is not None and p >= 0:
                        title = getattr(item, 'title', '').strip()
                        if title:
                            title = clean_text(title)
                            if p not in outline_map:
                                outline_map[p] = []
                            outline_map[p].append((level, title))
                except Exception:
                    pass
                    
    try:
        if reader.outline:
            _walk(reader.outline)
    except Exception:
        pass
        
    return outline_map


def is_heading_candidate(line: str, prev_ended: bool) -> bool:
    """Heuristic for detecting standalone subheadings within page body."""
    if not prev_ended:
        return False
    line = line.strip()
    if len(line) < 3 or len(line) > 60:
        return False
    if line.endswith(('.', ':', ';', ',', '!', '?', '"', '”', '’', '-')):
        return False
    words = line.split()
    if not words:
        return False
    # Check title case
    cap_count = sum(1 for w in words if w and (w[0].isupper() or w[0].isdigit() or w.lower() in {
        'and', 'or', 'the', 'in', 'of', 'to', 'for', 'a', 'an', 'with', 'on', 'at', 'by', 'from', 'is', 'are'
    }))
    return cap_count >= max(1, len(words) - 1)


def convert_pdf_to_md(pdf_path: str, output_path: str = None, quiet: bool = False) -> Tuple[int, int, float]:
    """
    Converts a single PDF to Markdown.
    Returns (total_pages, word_count, file_size_kb).
    """
    pdf_path = os.path.abspath(pdf_path)
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
    if not output_path:
        base_name = os.path.splitext(pdf_path)[0]
        # Clean potential redundant .epub or (WeLib.org) tags for cleaner markdown names
        clean_base = re.sub(r'\.epub$', '', base_name, flags=re.IGNORECASE)
        clean_base = re.sub(r'\s*--\s*\(\s*welib\.org\s*\)', '', clean_base, flags=re.IGNORECASE)
        output_path = f"{clean_base.strip()}.md"
    else:
        output_path = os.path.abspath(output_path)
        
    reader = pypdf.PdfReader(pdf_path)
    total_pages = len(reader.pages)
    outline_map = extract_outline(reader)
    
    doc_title = os.path.splitext(os.path.basename(pdf_path))[0]
    doc_title = clean_text(doc_title)
    
    md_lines: List[str] = [
        f"# {doc_title}\n\n",
        f"**Source**: `{os.path.basename(pdf_path)}`  \n",
        f"**Total Pages**: {total_pages}  \n\n",
        "---\n\n"
    ]
    
    current_paragraph: List[str] = []
    prev_ended = True

    for p_idx in range(total_pages):
        page = reader.pages[p_idx]
        try:
            raw_text = page.extract_text() or ""
        except Exception:
            raw_text = ""
            
        cleaned = clean_text(raw_text)
        page_lines = [l.strip() for l in cleaned.splitlines() if l.strip()]
        
        # Insert outline headings if this page starts one or more sections
        if p_idx in outline_map:
            if current_paragraph:
                md_lines.append(" ".join(current_paragraph) + "\n\n")
                current_paragraph = []
                prev_ended = True
                
            for lvl, title in outline_map[p_idx]:
                heading_hashes = "#" * min(lvl + 1, 4)
                md_lines.append(f"{heading_hashes} {title}\n\n")

        line_idx = 0
        while line_idx < len(page_lines):
            line = page_lines[line_idx]
            
            # Avoid repeating outline titles that are present at top of page text
            if p_idx in outline_map and line_idx < 4:
                redundant = False
                for _, title in outline_map[p_idx]:
                    if line == title or (line.isdigit() and str(line) in title) or (len(line) > 5 and line in title):
                        redundant = True
                        break
                if redundant:
                    line_idx += 1
                    continue
            
            # Subheading check
            if is_heading_candidate(line, prev_ended) and not current_paragraph:
                md_lines.append(f"### {line}\n\n")
                prev_ended = True
                line_idx += 1
                continue
            
            # De-hyphenate words broken over line wrap
            if current_paragraph:
                prev = current_paragraph[-1]
                if prev.endswith('-') and len(prev) > 1 and prev[-2].isalpha() and line and line[0].isalpha():
                    current_paragraph[-1] = prev[:-1] + line
                else:
                    current_paragraph.append(line)
            else:
                current_paragraph.append(line)
                
            # Paragraph termination heuristics
            is_terminal = any(line.endswith(p) for p in ('.', '!', '?', '”', '"', '’'))
            is_short = len(line) < 55
            
            if is_terminal and is_short:
                md_lines.append(" ".join(current_paragraph) + "\n\n")
                current_paragraph = []
                prev_ended = True
            else:
                prev_ended = False
                
            line_idx += 1
            
    if current_paragraph:
        md_lines.append(" ".join(current_paragraph) + "\n\n")
        
    full_markdown = "".join(md_lines)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_markdown)
        
    words = len(full_markdown.split())
    size_kb = os.path.getsize(output_path) / 1024
    
    if not quiet:
        print(f"✓ Converted '{os.path.basename(pdf_path)}' -> '{os.path.basename(output_path)}'")
        print(f"  Pages: {total_pages} | Words: {words:,} | Size: {size_kb:.1f} KB")
        
    return total_pages, words, size_kb


def main():
    parser = argparse.ArgumentParser(
        description="Convert PDF files to clean Markdown (.md) 100% locally with zero context bloat."
    )
    parser.add_argument("inputs", nargs="+", help="Path(s) to input PDF file(s)")
    parser.add_argument("-o", "--output", help="Output file path (only when converting a single PDF)")
    parser.add_argument("-d", "--out-dir", help="Output directory for converted markdown files")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet mode; minimal output")
    
    args = parser.parse_args()
    
    if args.output and len(args.inputs) > 1:
        parser.error("-o/--output can only be used with a single input file. Use -d/--out-dir for multiple files.")
        
    for inp in args.inputs:
        if args.out_dir:
            os.makedirs(args.out_dir, exist_ok=True)
            base = os.path.splitext(os.path.basename(inp))[0]
            clean_base = re.sub(r'\.epub$', '', base, flags=re.IGNORECASE)
            clean_base = re.sub(r'\s*--\s*\(\s*welib\.org\s*\)', '', clean_base, flags=re.IGNORECASE)
            out_file = os.path.join(args.out_dir, f"{clean_base.strip()}.md")
        elif args.output:
            out_file = args.output
        else:
            out_file = None
            
        try:
            convert_pdf_to_md(inp, out_file, quiet=args.quiet)
        except Exception as e:
            print(f"✗ Failed to convert {inp}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
