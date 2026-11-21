"""Collect the eight public site files without copying the source workbook or application."""

import argparse
import shutil
from pathlib import Path


def export(target):
    root = Path(__file__).resolve().parents[1]
    assets = {
        "index.html": "presentation/jury-page.html",
        "journey.html": "docs/jury/journey.html",
        "model.xlsx": "analysis/VK-Cases.xlsx",
        "slides.pdf": "presentation/Digital Cat$_strategy_msk.pdf",
        "team.svg": "presentation/assets/digital-cat.svg",
        "shop.webp": "presentation/assets/mac-shop.webp",
        "publication.webp": "docs/images/publication.webp",
    }
    target.mkdir(parents=True, exist_ok=True)
    for name, source in assets.items():
        shutil.copyfile(root / source, target / name)
    (target / ".nojekyll").touch()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    export(parser.parse_args().destination)
