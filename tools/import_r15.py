#!/usr/bin/env python3
"""Import the Release 1.5 baseline: the NIST test tool's conformance profiles and the 2018 guide's outline.

    python tools/import_r15.py --download        # fetch the profiles from the NIST/Valitheus test tool, then import
    python tools/import_r15.py                   # import the committed XML in prior/release-1.5/nist/ again
    python tools/import_r15.py --from DIR        # import per-profile downloads saved in DIR/<profile>/

The baseline for comparing this guide with Release 1.5 is:

- Format and validation (usage, cardinality, data types, lengths, value set bindings, conformance
  statements): the conformance profiles in NIST's Immunization Test Suite Edition 2
  (https://tools.valitheus.com/immunization-edition2/), built by NIST from the Release 1.5 2018 Update.
  This is what systems were tested and certified against. The tables in the 2018 PDF are not used.
- Everything else (guidance in the narrative): the 2018 Update PDF.

The test tool publishes each of the eight profiles separately, with the same segment and data type
libraries, value sets, bindings, and constraints. They are merged into one export in
prior/release-1.5/nist/ (committed: the profiles are public) and normalized into prior/release-1.5/model/
with the same code as the IGAMT import, so the two models can be compared field by field.

When the PDF is given (--pdf, or r15_pdf in inputs.json) it also writes prior/release-1.5/outline.yml,
the bookmarks with page ranges, and prior/release-1.5/text/ (requires PyMuPDF; maintainers only).
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guidecards import REPO, write_text, write_yaml  # noqa: E402
from import_igamt import FILES, build_model  # noqa: E402

PRIOR = REPO / "prior" / "release-1.5"
NIST_DIR = PRIOR / "nist"
MODEL_DIR = PRIOR / "model"

TOOL = "https://tools.valitheus.com/immunization-edition2"
# Test object id in the test tool -> profile folder name
PROFILES = {
    473: "VXU-Z22", 469: "ACK-Z23", 471: "QBP-Z34", 474: "QBP-Z44",
    475: "RSP-Z31", 470: "RSP-Z32", 476: "RSP-Z33", 472: "RSP-Z42",
}
# Test tool download name -> NIST export file name
DOWNLOADS = {
    "profile.xml": "Profile.xml",
    "constraints.zip": "Constraints.xml",
    "valuesetbindings.xml": "ValueSetBindings.xml",
    "valueset.xml": "ValueSets.xml",
    "coconstraints.xml": "CoConstraints.xml",
    "slicings.xml": "Slicings.xml",
}


# ---------------------------------------------------------------- download

def download(dest: Path) -> None:
    """Save each profile's files from the test tool's public documentation endpoint into dest/<profile>/."""
    for tid, name in PROFILES.items():
        (dest / name).mkdir(parents=True, exist_ok=True)
        for f in DOWNLOADS:
            body = urllib.parse.urlencode({"targetId": tid, "targetType": "TestObject", "targetTitle": name}).encode()
            req = urllib.request.Request(f"{TOOL}/api/hl7v2/documentation/{f}", data=body,
                                         headers={"User-Agent": "cdc-hl7-v2-guide-r2 import_r15"})
            with urllib.request.urlopen(req, timeout=180) as r:
                (dest / name / f).write_bytes(r.read())
        print(f"downloaded {name}")


def read_download(folder: Path, f: str) -> bytes:
    data = (folder / f).read_bytes()
    if f.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            xml = [n for n in z.namelist() if n.lower().endswith(".xml")]
            if len(xml) != 1:
                raise SystemExit(f"{folder / f}: expected one XML file, found {xml}")
            data = z.read(xml[0])
    return data


# ---------------------------------------------------------------- merge

def merge(src: Path, out: Path) -> None:
    """Merge the per-profile downloads into one NIST export (one Profile.xml with all eight messages)."""
    folders = [src / n for n in PROFILES.values()]
    missing = [str(p) for p in folders if not p.is_dir()]
    if missing:
        raise SystemExit(f"Missing profile downloads: {', '.join(missing)}")
    out.mkdir(parents=True, exist_ok=True)

    # Shared files must be identical across the profiles; keep one copy.
    for f, target in DOWNLOADS.items():
        if f == "profile.xml":
            continue
        copies = {read_download(p, f) for p in folders}
        if len(copies) != 1:
            raise SystemExit(f"{f} differs between profiles; merge by hand")
        (out / target).write_bytes(copies.pop())

    # Profile.xml: the libraries are shared; the Messages differ. Check, then combine.
    roots = [ET.parse(p / "profile.xml").getroot() for p in folders]
    for tag in ("Segments", "Datatypes"):
        if len({ET.tostring(r.find(tag)) for r in roots}) != 1:
            raise SystemExit(f"Profile.xml <{tag}> differs between profiles; merge by hand")
    merged = copy.deepcopy(roots[0])
    msgs = merged.find("Messages")
    for m in list(msgs):
        msgs.remove(m)
    for r in roots:
        for m in r.find("Messages"):
            msgs.append(copy.deepcopy(m))
    ET.indent(merged, space="  ")
    xml = ET.tostring(merged, encoding="unicode")
    (out / "Profile.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + xml + "\n", encoding="utf-8")


# ---------------------------------------------------------------- PDF outline and text

def import_pdf(pdf: Path) -> None:
    try:
        import pymupdf  # noqa: PLC0415
    except ImportError:
        try:
            import fitz as pymupdf  # noqa: PLC0415  (older PyMuPDF)
        except ImportError:
            raise SystemExit("Reading the PDF needs PyMuPDF (pip install pymupdf).")
    doc = pymupdf.open(pdf)
    toc = [(lvl, " ".join(title.replace("�", "-").split()), page) for lvl, title, page in doc.get_toc()]
    items = []
    for i, (lvl, title, page) in enumerate(toc):
        end = doc.page_count
        for lvl2, _, page2 in toc[i + 1:]:
            if lvl2 <= lvl:
                end = max(page, page2 - (0 if page2 == page else 1))
                break
        items.append({"level": lvl, "title": title, "pages": [page, end]})
    write_yaml(PRIOR / "outline.yml", {
        "source": pdf.name,
        "pages": doc.page_count,
        "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest()[:16],
        "outline": items,
    }, header="Generated by tools/import_r15.py from the PDF bookmarks. Do not edit.")
    text = PRIOR / "text"
    text.mkdir(parents=True, exist_ok=True)
    parts = []
    for n, page in enumerate(doc, 1):
        parts.append(f"=== page {n} ===\n{page.get_text().rstrip()}\n")
    write_text(text / "guide.txt", "\n".join(parts))
    print(f"{pdf.name}: {doc.page_count} pages, {len(items)} bookmarks -> outline.yml, text/guide.txt")


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--download", action="store_true", help="fetch the profiles from the test tool first")
    ap.add_argument("--from", dest="src", type=Path, help="per-profile downloads already saved in DIR/<profile>/")
    ap.add_argument("--pdf", type=Path, help="the 2018 Update PDF (default: r15_pdf in inputs.json, if set)")
    args = ap.parse_args()

    src = args.src
    if args.download:
        src = REPO / "output" / "r15-downloads"
        download(src)
    if src is not None:
        merge(src, NIST_DIR)
    missing = [f for f in FILES if not (NIST_DIR / f).exists()]
    if missing:
        ap.error(f"No NIST export in {NIST_DIR.relative_to(REPO)}; run with --download or --from DIR.")
    build_model(NIST_DIR, MODEL_DIR, generator="tools/import_r15.py",
                export_name="NIST Immunization Test Suite Edition 2 (tools.valitheus.com/immunization-edition2)")

    pdf = args.pdf
    if pdf is None and (REPO / "inputs.json").exists():
        val = json.loads((REPO / "inputs.json").read_text(encoding="utf-8")).get("r15_pdf")
        pdf = Path(val) if val else None
    if pdf is not None:
        import_pdf(pdf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
