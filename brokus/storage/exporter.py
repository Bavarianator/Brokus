"""Export engine for books in multiple formats."""

import json
import zipfile
from pathlib import Path
from typing import Optional
from xml.sax.saxutils import escape as xml_escape

from brokus.utils.logger import log
from brokus.storage.database import get_books_dir


class Exporter:
    """Exports generated books to MD, EPUB, PDF, DOCX, JSON, TXT."""

    def __init__(self, books_dir: Optional[Path] = None):
        self.books_dir = books_dir or get_books_dir()
        self.books_dir.mkdir(parents=True, exist_ok=True)

    def export(
        self,
        project: dict,
        chapters: list[dict],
        fmt: str = "md",
        language: str = "de",
    ) -> Path:
        """Export a book to the specified format.

        Args:
            project: Project dict from database
            chapters: List of chapter dicts from database
            fmt: One of 'md', 'epub', 'pdf', 'json', 'txt'
            language: Language code (e.g. 'de', 'en', 'fr')

        Returns:
            Path to the exported file
        """
        slug = self._make_slug(project["title"])
        exporters = {
            "md": self._export_markdown,
            "epub": self._export_epub,
            "pdf": self._export_pdf,
            "docx": self._export_docx,
            "json": self._export_json,
            "txt": self._export_txt,
        }

        if fmt not in exporters:
            raise ValueError(f"Unknown format: {fmt}")

        # Pass language to export methods via closure
        self._export_language = language
        output_path = exporters[fmt](project, chapters, slug)
        log.info(f"Exported '{project['title']}' to {fmt.upper()}: {output_path}")
        return output_path

    def export_multiple(
        self,
        project: dict,
        chapters: list[dict],
        formats: list[str],
        language: str = "de",
    ) -> list[Path]:
        """Export a book to multiple formats.

        Unknown formats are skipped (with a warning). Per-format errors
        (e.g. missing optional library) don't abort the whole batch.

        Args:
            project: Project dict from database
            chapters: List of chapter dicts from database
            formats: List of format keys, e.g. ['md', 'epub', 'json']
            language: Language code (e.g. 'de', 'en', 'fr')

        Returns:
            List of paths that were successfully exported.
        """
        valid = {"md", "epub", "pdf", "docx", "json", "txt"}
        results: list[Path] = []
        for fmt in formats:
            if fmt not in valid:
                log.warning(f"Skipping unknown format: {fmt}")
                continue
            try:
                path = self.export(project, chapters, fmt=fmt, language=language)
                results.append(path)
            except Exception as e:
                log.warning(f"Export to {fmt} failed: {e}")
        return results

    def _make_slug(self, title: str) -> str:
        """Create a filename-safe slug from a title."""
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in title).lower()

    def _export_markdown(
        self, project: dict, chapters: list[dict], slug: str
    ) -> Path:
        """Export as Markdown."""
        output = self.books_dir / f"{slug}.md"
        lines = [
            f"# {project['title']}",
            "",
            f"*Genre: {project['genre']}*",
            "",
            "---",
            "",
        ]

        if project.get("synopsis"):
            lines.extend([
                "## Synopsis",
                "",
                project["synopsis"],
                "",
                "---",
                "",
            ])

        for ch in chapters:
            if ch["status"] == "completed":
                lines.extend([
                    f"## Kapitel {ch['number']}: {ch['title']}",
                    "",
                    ch["text"].strip(),
                    "",
                    "---",
                    "",
                ])

        output.write_text("\n".join(lines), encoding="utf-8")
        return output

    def _export_epub(
        self, project: dict, chapters: list[dict], slug: str
    ) -> Path:
        """Export as EPUB using ebooklib."""
        from ebooklib import epub

        book = epub.EpubBook()
        book.set_identifier(f"brokus-{slug}")
        book.set_title(project["title"])
        book.set_language(getattr(self, '_export_language', 'de'))
        book.add_author("KI-generiert mit brokus")

        spine = ["nav"]
        chapter_items = []

        for ch in chapters:
            if ch["status"] != "completed":
                continue
            c = epub.EpubHtml(
                title=f"Kapitel {ch['number']}: {ch['title']}",
                file_name=f"chap_{ch['number']}.xhtml",
                lang=getattr(self, '_export_language', 'de'),
            )
            text = ch["text"].replace("\n", "<br/>")
            c.content = (
                f"<h2>Kapitel {ch['number']}: {ch['title']}</h2>"
                f"<p>{text}</p>"
            )
            book.add_item(c)
            spine.append(c)
            chapter_items.append(c)

        book.toc = chapter_items
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = spine

        output = self.books_dir / f"{slug}.epub"
        epub.write_epub(str(output), book)
        return output

    def _export_pdf(
        self, project: dict, chapters: list[dict], slug: str
    ) -> Path:
        """Export as PDF using weasyprint."""
        from weasyprint import HTML

        # Build HTML
        html_parts = [
            "<!DOCTYPE html>",
            f"<html lang='{getattr(self, '_export_language', 'de')}'>",
            "<head>",
            "<meta charset='utf-8'>",
            "<style>",
            "body { font-family: 'DejaVu Serif', serif; font-size: 11pt; line-height: 1.6; }",
            "h1 { text-align: center; font-size: 24pt; margin-bottom: 5pt; }",
            "h2 { font-size: 16pt; margin-top: 30pt; page-break-before: always; }",
            ".subtitle { text-align: center; font-style: italic; margin-bottom: 30pt; }",
            ".synopsis { font-style: italic; margin: 20pt 0; padding: 10pt; border-left: 3pt solid #333; }",
            "p { text-indent: 1.5em; margin: 0.5em 0; }",
            "</style>",
            f"<title>{project['title']}</title>",
            "</head>",
            "<body>",
            f"<h1>{project['title']}</h1>",
            f"<p class='subtitle'>Genre: {project['genre']}</p>",
        ]

        if project.get("synopsis"):
            html_parts.append(
                f"<div class='synopsis'><strong>Synopsis:</strong> {project['synopsis']}</div>"
            )

        for ch in chapters:
            if ch["status"] != "completed":
                continue
            text = ch["text"].replace("\n", "</p><p>")
            html_parts.append(f"<h2>Kapitel {ch['number']}: {ch['title']}</h2>")
            html_parts.append(f"<p>{text}</p>")

        html_parts.extend(["</body>", "</html>"])

        output = self.books_dir / f"{slug}.pdf"
        HTML(string="\n".join(html_parts)).write_pdf(str(output))
        return output

    def _export_docx(
        self, project: dict, chapters: list[dict], slug: str
    ) -> Path:
        """Export as DOCX using zipfile (no external library needed)."""
        title = project['title']
        genre = project.get('genre', '')

        # Build chapter XML paragraphs
        body_paragraphs = []

        # Title
        body_paragraphs.append(self._docx_heading(title, 0))
        body_paragraphs.append(self._docx_paragraph(f'Genre: {genre}', italic=True))
        body_paragraphs.append(self._docx_paragraph(''))

        for ch in chapters:
            if ch['status'] != 'completed':
                continue
            body_paragraphs.append(self._docx_heading(f"Kapitel {ch['number']}: {ch['title']}", 1))
            for para_text in ch['text'].split('\n'):
                if para_text.strip():
                    body_paragraphs.append(self._docx_paragraph(para_text.strip()))
                else:
                    body_paragraphs.append(self._docx_paragraph(''))

        # Build document.xml
        doc_xml = self._docx_document_xml(body_paragraphs)

        output = self.books_dir / f"{slug}.docx"
        with zipfile.ZipFile(str(output), 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('[Content_Types].xml', self._docx_content_types())
            zf.writestr('_rels/.rels', self._docx_rels())
            zf.writestr('word/_rels/document.xml.rels', self._docx_doc_rels())
            zf.writestr('word/document.xml', doc_xml)
            zf.writestr('word/styles.xml', self._docx_styles())
        return output

    @staticmethod
    def _docx_content_types() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            '</Types>'
        )

    @staticmethod
    def _docx_rels() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>'
        )

    @staticmethod
    def _docx_doc_rels() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '</Relationships>'
        )

    @staticmethod
    def _docx_styles() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>'
            '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:pPr><w:spacing w:before="480" w:after="120"/></w:pPr><w:rPr><w:b/><w:sz w:val="36"/><w:szCs w:val="36"/></w:rPr></w:style>'
            '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:pPr><w:spacing w:before="360" w:after="120"/></w:pPr><w:rPr><w:b/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr></w:style>'
            '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:pPr><w:jc w:val="center"/></w:pPr><w:rPr><w:b/><w:sz w:val="48"/><w:szCs w:val="48"/></w:rPr></w:style>'
            '</w:styles>'
        )

    @staticmethod
    def _docx_document_xml(paragraphs: list[str]) -> str:
        body = ''.join(paragraphs)
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f'<w:body>{body}'
            '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>'
            '</w:body></w:document>'
        )

    @staticmethod
    def _docx_heading(text: str, level: int) -> str:
        style = {0: 'Title', 1: 'Heading1', 2: 'Heading2'}.get(level, 'Heading2')
        esc = xml_escape(text)
        return f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr><w:r><w:t xml:space="preserve">{esc}</w:t></w:r></w:p>'

    @staticmethod
    def _docx_paragraph(text: str, italic: bool = False) -> str:
        esc = xml_escape(text)
        rpr = '<w:rPr><w:i/></w:rPr>' if italic else ''
        return f'<w:p>{rpr}<w:r><w:t xml:space="preserve">{esc}</w:t></w:r></w:p>'

    def _export_json(
        self, project: dict, chapters: list[dict], slug: str
    ) -> Path:
        """Export as JSON."""

        export_data = {
            "title": project["title"],
            "genre": project["genre"],
            "idea": project["idea"],
            "synopsis": project.get("synopsis", ""),
            "total_chapters": project.get("total_chapters", 0),
            "chapters": [
                {
                    "number": ch["number"],
                    "title": ch["title"],
                    "text": ch["text"],
                    "word_count": ch.get("word_count", 0),
                    "compliance_score": ch.get("compliance_score"),
                }
                for ch in chapters
                if ch["status"] == "completed"
            ],
        }

        output = self.books_dir / f"{slug}.json"
        output.write_text(json.dumps(export_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return output

    def _export_txt(
        self, project: dict, chapters: list[dict], slug: str
    ) -> Path:
        """Export as plain text."""
        output = self.books_dir / f"{slug}.txt"
        lines = [
            project["title"],
            f"Genre: {project['genre']}",
            "",
        ]

        for ch in chapters:
            if ch["status"] == "completed":
                lines.extend([
                    f"--- Kapitel {ch['number']}: {ch['title']} ---",
                    "",
                    ch["text"].strip(),
                    "",
                ])

        output.write_text("\n".join(lines), encoding="utf-8")
        return output
