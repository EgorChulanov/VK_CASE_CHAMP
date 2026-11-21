"""Check the exported PDF, its link targets, embedded fonts, team slide and QR codes."""

import argparse
from pathlib import Path
import pypdfium2
from pypdf import PdfReader
import zxingcpp


def verify(path, preview_dir=None):
    public = "https://egorchulanov.github.io/vk-case-2026/"
    expected = {6: public + "journey.html", 7: public + "prototype/", 12: public + "model.xlsx", 14: public}
    reader = PdfReader(path)
    rendered = pypdfium2.PdfDocument(path)
    assert len(reader.pages) == len(rendered) == 14
    all_fonts = set()
    qr_count = 0
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        assert not any(mark in text for mark in ("\u2014", "\u00b7", "\u2022")), (i, "punctuation")
        words = " ".join(text.lower().split())
        assert not any(
            t in words
            for t in (
                "где путь расходится",
                "сентябрьская связь между просмотрами",
                "оценки проверим в интервью",
                "вклад инструмента проверит эксперимент",
                "коротко о решении",
                "два окна",
                "методика использования",
            )
        ), i
        if i == len(reader.pages):
            for required in (
                "как использовали ии",
                "openai codex",
                "whisper",
                "imagegen",
                "apple vision",
                "предложение команды",
                "по исходной книге",
                "до выдачи заказа",
            ):
                assert required in words, (i, required)
        else:
            assert "как использовали ии" not in words, i
        assert float(page.mediabox.width) / float(page.mediabox.height) == 16 / 9
        fonts = page["/Resources"].get("/Font", {})
        for font in fonts.values():
            obj = font.get_object()
            all_fonts.add(str(obj.get("/BaseFont", "")))
        urls = []
        for link in page.get("/Annots", []):
            annotation = link.get_object()
            dest = annotation.get("/Dest")
            if isinstance(dest, str):
                assert dest in reader.named_destinations, (i, dest)
            action = annotation.get("/A")
            if action and action.get("/URI"):
                url = str(action["/URI"])
                assert not any(
                    t in url
                    for t in ["file:", "localhost", "127.0.0.1", "/VK_CASE_CHAMP"]
                ), url
                urls.append(url)
        if i == 1:
            assert "москва, 2026" in words and "digital cat$" in words
        if i == 2:
            compact = " ".join(text.split())
            for education_line in ("Высшая школа экономики, 2-й курс", "«Управление цифровым продуктом»"):
                assert compact.count(education_line) == 4, (i, education_line)
            for name, role in (
                ("Егор Чуланов", "Продукт и прототип"),
                ("Екатерина Макаренко", "Исследование и путь покупателя"),
                ("Максим Ширяев", "Данные и эксперимент"),
                ("Анфиса Опарина", "Экономика и запуск"),
            ):
                assert name in compact and role in compact, (i, name, role)
            assert all(label not in words for label in ("москва", "2026", "темы на защите")), i
            portraits = set()
            for obj in page["/Resources"].get("/XObject", {}).values():
                resource = obj.get_object()
                if resource.get("/Subtype") == "/Image" and resource.get("/Width", 0) >= 140 and resource.get("/Height", 0) >= 160:
                    portraits.add(obj.idnum)
            assert len(portraits) >= 4, (i, "portraits", len(portraits))
        if i == 6:
            assert "Карта пути продавца и покупателя" in " ".join(text.split())
        # Rasterization uses the actual PDF. The QR must decode at normal screen size.
        raster = rendered[i - 1].render(scale=4 / 3).to_pil().convert("RGB")
        codes = [c.text for c in zxingcpp.read_barcodes(raster) if c.text]
        if i in expected:
            assert codes == [expected[i]] and expected[i] in urls, (i, codes, urls)
            qr_count += 1
        else:
            assert not codes, (i, codes)
        if preview_dir:
            preview_dir.mkdir(parents=True, exist_ok=True)
            raster.save(preview_dir / f"{i:02d}.jpg", quality=88)
    assert any("VKSansText" in name for name in all_fonts), all_fonts
    assert any("VKSansDisplay" in name for name in all_fonts), all_fonts
    print(
        f"PDF: {len(reader.pages)} страниц, {qr_count} читаемых QR, навигация и обе гарнитуры проверены."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "pdf",
        type=Path,
        nargs="?",
        default=Path(__file__).with_name("Digital Cat$_strategy_msk.pdf"),
    )
    parser.add_argument("--previews", type=Path)
    args = parser.parse_args()
    verify(args.pdf, args.previews)
