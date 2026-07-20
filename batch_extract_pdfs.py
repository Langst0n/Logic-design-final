#!/usr/bin/env python3
"""
batch_extract_pdfs.py

Extracts pages from MULTIPLE PDFs into one output folder, at a controlled DPI,
with filenames that track which source PDF and page number each image came from.

Usage:
    python3 batch_extract_pdfs.py output_folder/ book1.pdf book2.pdf book3.pdf
    python3 batch_extract_pdfs.py output_folder/ *.pdf --dpi 300

Each image is named: <pdf_stem>_page_###.png
e.g. digitallogic_page_001.png, digitallogic_page_002.png, chapter2_page_001.png

Install dependency first:
    pip install pymupdf --break-system-packages
"""

import argparse
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Missing dependency. Install it with:\n\n  pip install pymupdf --break-system-packages\n")
    sys.exit(1)


def extract_pdf(pdf_path: Path, output_dir: Path, dpi: int) -> list[Path]:
    doc = fitz.open(pdf_path)
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    stem = pdf_path.stem.replace(" ", "_")

    saved = []
    for i in range(len(doc)):
        page = doc[i]
        pix = page.get_pixmap(matrix=matrix)
        out_path = output_dir / f"{stem}_page_{i + 1:03d}.png"
        pix.save(out_path)
        saved.append(out_path)
    doc.close()
    return saved


def main():
    parser = argparse.ArgumentParser(description="Extract pages from multiple PDFs as high-res PNGs.")
    parser.add_argument("output_dir", help="Folder to write all PNGs into")
    parser.add_argument("pdfs", nargs="+", help="One or more PDF file paths")
    parser.add_argument("--dpi", type=int, default=300, help="Resolution (default: 300)")

    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    total_images = 0
    manifest_lines = ["source_pdf,page_number,image_file"]

    for pdf_str in args.pdfs:
        pdf_path = Path(pdf_str)
        if not pdf_path.exists():
            print(f"Skipping missing file: {pdf_path}")
            continue

        print(f"Processing {pdf_path.name}...")
        saved = extract_pdf(pdf_path, output_dir, args.dpi)
        total_images += len(saved)
        print(f"  -> {len(saved)} pages extracted")

        for idx, img_path in enumerate(saved, start=1):
            manifest_lines.append(f"{pdf_path.name},{idx},{img_path.name}")

    manifest_path = output_dir / "manifest.csv"
    manifest_path.write_text("\n".join(manifest_lines))

    print(f"\nDone. {total_images} total images written to {output_dir}/")
    print(f"Manifest written to {manifest_path}")


if __name__ == "__main__":
    main()
