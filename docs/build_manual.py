#!/usr/bin/env python3
"""Renderiza docs/manual.html a manual-instalacion.pdf (raíz del repositorio).

Requiere weasyprint (`python3 -m pip install weasyprint`). En macOS con Homebrew, si
weasyprint no encuentra libgobject/pango/cairo:

    DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 docs/build_manual.py

Uso: python3 docs/build_manual.py
"""
from pathlib import Path

from weasyprint import HTML

DOCS_DIR = Path(__file__).resolve().parent
REPO_DIR = DOCS_DIR.parent


def main():
    html_path = DOCS_DIR / "manual.html"
    pdf_path = REPO_DIR / "manual-instalacion.pdf"
    HTML(str(html_path)).write_pdf(str(pdf_path))
    print(f"PDF generado: {pdf_path}")


if __name__ == "__main__":
    main()
