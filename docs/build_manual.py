#!/usr/bin/env python3
"""Renderiza docs/manual.html a manual-instalacion.pdf (raíz del repositorio).

Requiere weasyprint (`python3 -m pip install weasyprint`). En macOS con Homebrew, si
weasyprint no encuentra libgobject/pango/cairo:

    DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 docs/build_manual.py

Uso: python3 docs/build_manual.py [--chrome]

Con --chrome imprime con Chrome/Edge headless en vez de weasyprint: sirve en Windows, donde
weasyprint suele fallar por sus librerías nativas (pango/fontconfig). Las fuentes salen de las
instaladas en la máquina, así que el PDF puede variar un poco respecto al de macOS.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent
REPO_DIR = DOCS_DIR.parent


def main():
    html_path = DOCS_DIR / "manual.html"
    pdf_path = REPO_DIR / "manual-instalacion.pdf"
    if "--chrome" in sys.argv:
        build_with_chrome(html_path, pdf_path)
    else:
        from weasyprint import HTML
        HTML(str(html_path)).write_pdf(str(pdf_path))
    print(f"PDF generado: {pdf_path}")


def find_chrome():
    candidates = [
        shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chrome"),
        shutil.which("msedge"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    sys.exit("No se encontró Chrome ni Edge para imprimir el PDF.")


def build_with_chrome(html_path, pdf_path):
    subprocess.run([find_chrome(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf_path}", html_path.as_uri()],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
