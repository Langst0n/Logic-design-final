#!/usr/bin/env python3
"""
analyze_images.py

Sends each extracted page image to Claude for in-depth problem-solving analysis,
and asks Claude to explicitly flag anything on the page it had trouble reading
(blurry text, ambiguous diagram labels, overlapping arrows, etc.) so you know
exactly which pages need a zoomed-in re-extraction.

Requires:
    pip install anthropic --break-system-packages
    export ANTHROPIC_API_KEY=your_key_here

Usage:
    python3 analyze_images.py ./pages_out/ ./analysis_out/
"""

import base64
import os
import sys
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("Missing dependency. Install it with:\n\n  pip install anthropic --break-system-packages\n")
    sys.exit(1)

ANALYSIS_PROMPT = """You are looking at one page from a textbook, likely covering digital logic /
state machine design or a related technical topic.

Do two things, clearly separated:

1. READABILITY CHECK (do this first, be honest and specific):
   If anything on the page is hard to read with confidence — a diagram
   label, an arrow direction, a small table value, faint text — say so
   explicitly under a "READABILITY ISSUES:" heading, describing exactly
   what element is ambiguous and why. If everything is fully legible,
   write "READABILITY ISSUES: none."

2. ANALYSIS:
   Give an in-depth walkthrough of any problems, examples, or concepts on
   this page: what's being taught, how any example problem is solved step
   by step, and any state tables / diagrams / traces explained in your own
   words. If the page is not a worked problem (e.g. a title page or pure
   text), summarize the key concept instead.
"""


def encode_image(path: Path) -> str:
    return base64.standard_b64encode(path.read_bytes()).decode("utf-8")


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 analyze_images.py <images_folder> <output_folder>")
        sys.exit(1)

    images_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: set ANTHROPIC_API_KEY in your environment first.")
        sys.exit(1)

    client = anthropic.Anthropic()

    image_paths = sorted(images_dir.glob("*.png"))
    if not image_paths:
        print(f"No .png files found in {images_dir}")
        sys.exit(1)

    flagged_pages = []

    for img_path in image_paths:
        print(f"Analyzing {img_path.name}...")
        image_b64 = encode_image(img_path)

        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_b64,
                                },
                            },
                            {"type": "text", "text": ANALYSIS_PROMPT},
                        ],
                    }
                ],
            )
        except Exception as e:
            print(f"  ERROR analyzing {img_path.name}: {e}")
            continue

        text = "".join(block.text for block in response.content if block.type == "text")

        # Save full analysis per page
        out_path = output_dir / f"{img_path.stem}.md"
        out_path.write_text(f"# Analysis: {img_path.name}\n\n{text}\n")

        # Track flagged pages for a summary file
        if "READABILITY ISSUES: none" not in text:
            flagged_pages.append(img_path.name)

        print(f"  -> saved {out_path.name}")

    # Write summary of anything flagged
    summary_path = output_dir / "_FLAGGED_PAGES.txt"
    if flagged_pages:
        summary_path.write_text(
            "Pages with readability issues (re-check / re-extract with --crop):\n\n"
            + "\n".join(flagged_pages)
        )
        print(f"\n{len(flagged_pages)} page(s) flagged for readability issues.")
        print(f"See {summary_path}")
    else:
        summary_path.write_text("No pages flagged for readability issues.")
        print("\nNo pages flagged for readability issues.")


if __name__ == "__main__":
    main()
