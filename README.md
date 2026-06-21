# Threads Seminar — presentation

Two output formats from one design, on an **ivory matte texture** background.

## 1. Web (HTML) — for GitHub Pages
`index.html` — reveal.js 5 + Tailwind, 16:9 (1280×720).

- Open `index.html` in a browser to present (arrow keys / space to navigate).
- To host: push to a repo and enable **Settings → Pages → Deploy from branch → root**. The deck is at `https://<user>.github.io/<repo>/`.
- Dependencies load from CDN (Tailwind, reveal.js, Google Fonts), so the page needs internet when viewed.

## 2. PDF
Two ways to generate it:

**a) Offline renderer (used here)** — `build_pdf.py`
Reproduces the ivory texture and renders each slide with reportlab. No browser needed.
```
python3 build_pdf.py        # -> threads-seminar.pdf
```
Slide content lives in the `SLIDES` list, kept in sync with `index.html`.

**b) Browser-faithful (pixel-exact to the web deck)** — needs internet + Chrome locally
```
npx decktape reveal index.html threads-seminar.pdf --size 1280x720
```

## Design tokens
| token        | value     |
|--------------|-----------|
| ivory base   | `#F6F1E7` |
| ivory light  | `#FBF8F0` |
| ivory deep   | `#ECE4D4` |
| ink          | `#2B2723` |
| ink soft     | `#6B6358` |
| accent (clay)| `#CC785C` |

**Font:** one consistent Anthropic-style sans throughout. Anthropic's real brand
fonts (Styrene / Tiempos) are licensed and can't be hosted on the web, so the
stack leads with their names (used if you have them installed) and falls back to
**Noto Sans KR** — a clean, free, Korean-supporting match. The PDF embeds **Noto
Sans CJK KR**, the same design.

> Send slide details and I'll build them out across both formats.
