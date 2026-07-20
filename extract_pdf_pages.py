#!/usr/bin/env python3
"""
extract_pdf_pages.py

Extracts every page of a PDF as a high-resolution PNG image, suitable for
feeding into Claude (or any vision model) for diagram-heavy textbook content.

Why this exists:
- PDFs get inconsistently rendered/downsampled by different tools.
- Extracting each page yourself at a controlled DPI avoids double-compression
  and gives you one image file per page — easy to debug if a specific page
  doesn't read correctly.

Usage:
    python3 extract_pdf_pages.py input.pdf output_folder/
    python3 extract_pdf_pages.py input.pdf output_folder/ --dpi 300
    python3 extract_pdf_pages.py input.pdf output_folder/ --pages 1-20
    python3 extract_pdf_pages.py input.pdf output_folder/ --crop 45,50,44,20 --crop-pages 12,13

Install dependency first:
    pip install pymupdf --break-system-packages
    (or just `pip install pymupdf` if you're not on a system-managed Python)
"""

import argparse
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Missing dependency. Install it with:\n\n  pip install pymupdf --break-system-packages\n")
    sys.exit(1)


def parse_page_range(spec: str, max_pages: int) -> list[int]:
    """Parse '1-20' or '1,3,5-10' into a sorted list of 0-indexed page numbers."""
    if not spec:
        return list(range(max_pages))
    pages = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-")
            pages.update(range(int(start) - 1, int(end)))
        else:
            pages.add(int(part) - 1)
    return sorted(p for p in pages if 0 <= p < max_pages)


def parse_crop_pages(spec: str) -> set[int]:
    """Parse '12,13' into a set of 1-indexed page numbers to also crop."""
    if not spec:
        return set()
    return {int(p.strip()) for p in spec.split(",")}


def main():
    parser = argparse.ArgumentParser(description="Extract PDF pages as high-res PNGs.")
    parser.add_argument("input_pdf", help="Path to the source PDF")
    parser.add_argument("output_dir", help="Folder to write PNGs into")
    parser.add_argument("--dpi", type=int, default=300,
                         help="Resolution for extraction (default: 300). "
                              "Use 300-400 for pages with fine diagram labels.")
    parser.add_argument("--pages", type=str, default="",
                         help="Optional page range, e.g. '1-20' or '1,3,5-10'. "
                              "Default: all pages.")
    parser.add_argument("--crop", type=str, default="",
                         help="Optional crop box as percentages 'left,top,right,bottom' "
                              "(e.g. '45,50,100,90' = right half, bottom half of page). "
                              "Produces an EXTRA zoomed-in image alongside the full page.")
    parser.add_argument("--crop-pages", type=str, default="",
                         help="1-indexed page numbers to apply --crop to, e.g. '12,13'. "
                              "If omitted but --crop is set, crop is applied to all pages.")
    parser.add_argument("--prefix", type=str, default="page",
                         help="Filename prefix (default: 'page' -> page_001.png)")

    args = parser.parse_args()

    input_path = Path(args.input_pdf)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        print(f"Error: {input_path} does not exist.")
        sys.exit(1)

    doc = fitz.open(input_path)
    total_pages = len(doc)
    page_indices = parse_page_range(args.pages, total_pages)
    crop_page_set = parse_crop_pages(args.crop_pages)

    # zoom factor: PyMuPDF's default render is 72 DPI, so scale accordingly
    zoom = args.dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    crop_box = None
    if args.crop:
        try:
            l, t, r, b = (float(x) / 100 for x in args.crop.split(","))
            crop_box = (l, t, r, b)
        except ValueError:
            print("Error: --crop must be 'left,top,right,bottom' as percentages, e.g. '45,50,100,90'")
            sys.exit(1)

    print(f"Extracting {len(page_indices)} of {total_pages} pages at {args.dpi} DPI...")

    for i in page_indices:
        page = doc[i]
        page_num = i + 1  # 1-indexed for filenames/messages

        # Full page render
        pix = page.get_pixmap(matrix=matrix)
        out_path = output_dir / f"{args.prefix}_{page_num:03d}.png"
        pix.save(out_path)
        print(f"  saved {out_path.name} ({pix.width}x{pix.height})")

        # Optional extra cropped/zoomed render for diagram-heavy pages
        should_crop = crop_box is not None and (not crop_page_set or page_num in crop_page_set)
        if should_crop:
            rect = page.rect
            l, t, r, b = crop_box
            clip = fitz.Rect(
                rect.width * l, rect.height * t,
                rect.width * r, rect.height * b,
            )
            crop_pix = page.get_pixmap(matrix=matrix, clip=clip)
            crop_out_path = output_dir / f"{args.prefix}_{page_num:03d}_crop.png"
            crop_pix.save(crop_out_path)
            print(f"  saved {crop_out_path.name} ({crop_pix.width}x{crop_pix.height}) [cropped]")

    doc.close()
    print("Done.")


if __name__ == "__main__":
    main()
