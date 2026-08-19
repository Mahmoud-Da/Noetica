import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz

from app.pdf_translator import translate_pdf


class PdfTranslatorTests(unittest.TestCase):
    @patch("app.pdf_translator.Translator")
    def test_output_contains_only_selected_page_range(self, _translator: object) -> None:
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.pdf"
            output_path = Path(directory) / "output.pdf"
            source = fitz.open()
            try:
                for page_number in range(1, 7):
                    source.new_page(width=500 + page_number, height=700)
                source.save(input_path)
            finally:
                source.close()

            messages: list[str] = []
            translate_pdf(
                input_path,
                output_path,
                "English",
                "Arabic",
                3,
                5,
                lambda _progress, message: messages.append(message),
            )

            with fitz.open(output_path) as result:
                self.assertEqual(result.page_count, 3)
                self.assertEqual(
                    [round(page.rect.width) for page in result],
                    [503, 504, 505],
                )

            self.assertIn("Extracting page 3 of 6.", messages)
            self.assertIn("Finished page 5 of 6.", messages)


if __name__ == "__main__":
    unittest.main()
