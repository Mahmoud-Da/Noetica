from collections.abc import Callable
from pathlib import Path

import fitz

from .groq_client import Translator

Progress = Callable[[float, str], None]


def _span_text(line: dict) -> str:
    return "".join(span.get("text", "") for span in line.get("spans", [])).strip()


def _line_style(line: dict) -> tuple[float, tuple[float, float, float]]:
    spans = line.get("spans", [])
    if not spans:
        return 10, (0, 0, 0)
    span = spans[0]
    color = span.get("color", 0)
    red = ((color >> 16) & 255) / 255
    green = ((color >> 8) & 255) / 255
    blue = (color & 255) / 255
    return float(span.get("size", 10)), (red, green, blue)


def _fit_text(page: fitz.Page, rect: fitz.Rect, text: str, font_size: float, color: tuple[float, float, float]) -> None:
    size = min(font_size, rect.height * 0.82)
    while size >= 4:
        shape = page.new_shape()
        overflow = shape.insert_textbox(
            rect,
            text,
            fontsize=size,
            fontname="helv",
            color=color,
            align=fitz.TEXT_ALIGN_LEFT,
        )
        if overflow >= 0:
            shape.commit()
            return
        size -= 0.5
    page.insert_textbox(rect, text, fontsize=4, fontname="helv", color=color, align=fitz.TEXT_ALIGN_LEFT)


def translate_pdf(
    input_path: Path,
    output_path: Path,
    source_language: str,
    target_language: str,
    progress: Progress,
) -> None:
    translator = Translator()
    document = fitz.open(input_path)
    total_pages = max(document.page_count, 1)

    try:
        for page_index, page in enumerate(document):
            page_number = page_index + 1
            progress((page_index / total_pages) * 100, f"Extracting page {page_number} of {total_pages}.")
            text_page = page.get_text("dict")
            replacements: list[tuple[fitz.Rect, str, float, tuple[float, float, float]]] = []

            for block in text_page.get("blocks", []):
                if block.get("type") != 0:
                    continue
                line_entries: list[tuple[fitz.Rect, str, float, tuple[float, float, float]]] = []
                for line in block.get("lines", []):
                    original = _span_text(line)
                    if not original:
                        continue
                    rect = fitz.Rect(line["bbox"])
                    font_size, color = _line_style(line)
                    line_entries.append((rect, original, font_size, color))

                originals = [entry[1] for entry in line_entries]
                translated_lines = translator.translate_lines(originals, source_language, target_language)
                for (rect, _original, font_size, color), translated in zip(line_entries, translated_lines, strict=True):
                    replacements.append((rect, translated, font_size, color))

            progress(
                ((page_index + 0.55) / total_pages) * 100,
                f"Redrawing translated text on page {page_number} of {total_pages}.",
            )

            for rect, translated, font_size, color in replacements:
                page.add_redact_annot(rect, fill=(1, 1, 1))
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

            for rect, translated, font_size, color in replacements:
                _fit_text(page, rect, translated, font_size, color)

            progress((page_number / total_pages) * 100, f"Finished page {page_number} of {total_pages}.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        document.save(output_path, garbage=4, deflate=True)
    finally:
        document.close()
