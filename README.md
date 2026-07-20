# PDF Diagram Analyzer

Extracts pages from textbook PDFs as high-resolution images and uses Claude
to generate in-depth problem-solving analysis for each page, flagging any
pages where diagrams, tables, or labels are hard to read so they can be
re-extracted at higher resolution or cropped.

## Setup

```bash
pip install pymupdf anthropic --break-system-packages
export ANTHROPIC_API_KEY=your_key_here
```

## Usage

### 1. Extract pages from one or more PDFs

```bash
python3 batch_extract_pdfs.py ./pages_out/ book1.pdf book2.pdf book3.pdf
```

Writes one PNG per page into `pages_out/`, named `<pdf_stem>_page_###.png`,
plus a `manifest.csv` tracking which image came from which source PDF.

Options:
- `--dpi 300` (default) — bump to 400 for pages with fine diagram labels

### 2. Run analysis + readability check

```bash
python3 analyze_images.py ./pages_out/ ./analysis_out/
```

Sends each image to Claude, saves an `.md` file per page with:
- A readability check (flags anything ambiguous or hard to read)
- An in-depth walkthrough of any worked problems, diagrams, or tables on the page

Writes `_FLAGGED_PAGES.txt` at the end listing any pages that need a closer look.

### 3. Re-extract flagged pages with a crop (optional, single-PDF only)

For any page in `_FLAGGED_PAGES.txt`, use the single-PDF script with `--crop`
to get a zoomed-in image of just the problem region:

```bash
python3 extract_pdf_pages.py book1.pdf ./pages_out/ \
  --crop 45,25,80,75 --crop-pages 12,13 --dpi 400
```

Then re-run `analyze_images.py` on just those files.

## Notes

- Source PDFs and generated images are gitignored — don't commit copyrighted
  textbook content to the repo. Keep them local to your working session.
- Analysis runs are one API call per page, so ~90 pages means ~90 calls —
  test on a small subset first before running the full batch.
