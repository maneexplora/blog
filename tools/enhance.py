#!/usr/bin/env python3
"""Corrección automática suave para las fotos de Manuel (blog, carrusel e historias).

Uso:  python3 tools/enhance.py <carpeta_origen> <carpeta_destino> origen1.jpg:destino1.jpg [...]
      (sin pares: procesa todas las .jpg con el mismo nombre)

Qué hace, sin filtros ni cambios de estilo:
  - endereza según EXIF y reduce a 1400 px máximo (lado largo)
  - balance de blancos suave (gray world al 20 %): quita el tono amarillo de interiores
  - autocontraste con recorte mínimo (0.5 %) para dar profundidad
  - aclara solo si la foto está oscura (brillo medio < 105)
  - +6 % de saturación y nitidez suave (unsharp mask)
"""
import os, sys
from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageStat

def enhance(im, max_side=1400):
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((max_side, max_side), Image.LANCZOS)
    # balance de blancos suave
    r, g, b = ImageStat.Stat(im).mean
    avg = (r + g + b) / 3
    k = 0.2   # suave: la comida debe conservar su calidez
    gains = [1 + k * (avg / c - 1) if c else 1 for c in (r, g, b)]
    ch = [c.point(lambda v, f=f: min(255, int(v * f))) for c, f in zip(im.split(), gains)]
    im = Image.merge("RGB", ch)
    # contraste
    im = ImageOps.autocontrast(im, cutoff=0.5)
    # brillo solo si está oscura
    lum = ImageStat.Stat(im.convert("L")).mean[0]
    if lum < 105:
        im = ImageEnhance.Brightness(im).enhance(min(1.25, 115 / lum))
    im = ImageEnhance.Color(im).enhance(1.06)
    im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=3))
    return im

def main(src, dst, pairs):
    os.makedirs(dst, exist_ok=True)
    if not pairs:
        pairs = [f"{f}:{f}" for f in sorted(os.listdir(src)) if f.lower().endswith((".jpg", ".jpeg"))]
    for p in pairs:
        a, b = p.split(":", 1)
        out = enhance(Image.open(os.path.join(src, a)))
        out.save(os.path.join(dst, b), quality=86, optimize=True, progressive=True)
        print(b, out.size)

if __name__ == "__main__":
    if len(sys.argv) < 3: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
