"""Assemble the jury site from the published materials and the browser build."""

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
        "phone-clip.webp": "presentation/assets/phone-clip.webp",
        "publication.webp": "docs/images/publication.webp",
    }
    for face in ("VKSansText-Regular", "VKSansText-Medium", "VKSansText-DemiBold", "VKSansDisplayExpanded-Bold"):
        name = "fonts/" + face + ".woff2"
        assets[name] = "presentation/" + name

    dist = root / "demo/dist"
    if not (dist / "index.html").is_file() or not (dist / "shop.js").is_file():
        raise FileNotFoundError("Сначала соберите браузерную версию магазина в demo/dist")
    public_extensions = {".html", ".css", ".js", ".mjs", ".woff", ".woff2", ".svg", ".webp", ".jpg", ".png", ".mp4", ".webm", ".vtt"}
    for source in sorted(dist.rglob("*")):
        if source.is_file():
            if source.suffix.lower() not in public_extensions:
                raise ValueError(f"Проверьте назначение файла сборки {source.name}")
            name = Path("prototype") / source.relative_to(dist)
            assets[name] = source.relative_to(root)

    for name, source in assets.items():
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / source, destination)
    (target / ".nojekyll").touch()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    export(parser.parse_args().destination)
