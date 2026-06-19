"""Sobe nada — assume o app já rodando — e tira screenshot do dashboard.

Uso: python scripts/screenshot_dashboard.py http://127.0.0.1:8050 out.png
"""
from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8050/"
out = sys.argv[2] if len(sys.argv) > 2 else "dashboard.png"
errors: list[str] = []

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 1600})
    page.on("console", lambda m: errors.append(f"{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(2500)  # deixa o Chart.js desenhar
    page.screenshot(path=out, full_page=True)
    browser.close()

print("SCREENSHOT:", out)
if errors:
    print("JS ERRORS:")
    for e in errors:
        print(" -", e)
else:
    print("JS ERRORS: nenhum")
