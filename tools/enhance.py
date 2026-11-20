#!/usr/bin/env python3
"""Corrección automática de las fotos de Manuel (blog, carrusel e historias). v2

Uso:  python3 tools/enhance.py <origen> <destino> [--ig] origen1.jpg:destino1.jpg[@cx] [...]
      --ig   además genera ig/<destino> recortado a 4:5 (1080x1350) DESDE LA FOTO ORIGINAL
      @cx    centro horizontal del recorte 4:5 (0–1, por defecto 0.5)

Cambios v2 (feedback nov-2026: fotos de noche quemadas y poco nítidas):
  - Nunca se escala hacia arriba: el recorte 4:5 se hace sobre la resolución completa
    y luego se reduce a 1080x1350. La v1 recortaba sobre una copia de 1400 px y la
    ampliaba, por eso salían suaves.
  - Fotos de noche (brillo medio bajo): NO se aclara ni se estira el contraste;
    solo se levantan un poco las sombras con una curva que protege las luces.
  - Fotos de día: autocontraste solo en las sombras, luces con curva suave (sin recorte).
  - Control de calidad: si la edición quema más del 0.5 % de píxeles que el original,
    se descarta la edición y se usa la foto original solo redimensionada y con nitidez.
  - JPEG calidad 92 sin submuestreo de color.
"""
import os, sys
from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageStat

BLOG_MAX = 1400
IG_W, IG_H = 1080, 1350


def clipped(im, t=250):
    h = im.convert("L").histogram()
    return sum(h[t:]) / max(1, sum(h))


def curve(shadow_lift=0.0, black=0, white=255):
    """LUT: estira negros y levanta sombras; las luces no se tocan (no se queman)."""
    lut = []
    for v in range(256):
        x = min(1.0, max(0.0, (v - black) / max(1, white - black)))
        x = x + shadow_lift * x * (1 - x) ** 2 * 4          # sombras arriba, medios casi igual
        lut.append(int(round(min(1.0, max(0.0, x)) * 255)))
    return lut


def correct(im):
    """Devuelve la foto corregida, con la misma resolución."""
    base_clip = clipped(im)
    lum = ImageStat.Stat(im.convert("L")).mean[0]
    night = lum < 90
    # balance de blancos muy suave (de noche casi nada: las luces cálidas son parte de la foto)
    r, g, b = ImageStat.Stat(im).mean
    avg = (r + g + b) / 3
    k = 0.05 if night else 0.15
    gains = [1 + k * (avg / c - 1) if c else 1 for c in (r, g, b)]
    out = Image.merge("RGB", [c.point(lambda v, f=f: min(255, int(v * f))) for c, f in zip(im.split(), gains)])
    # punto negro desde el histograma (0.3 %), sin tocar el blanco
    h = out.convert("L").histogram(); n = sum(h); acc = 0; black = 0
    for i, c in enumerate(h):
        acc += c
        if acc > n * 0.003:
            black = min(i, 20); break
    lut = curve(shadow_lift=0.10 if night else 0.06, black=black, white=255)
    out = out.point(lut * 3)
    out = ImageEnhance.Color(out).enhance(1.04)
    if clipped(out) - base_clip > 0.005:     # control de calidad: no quemar
        return im, False
    return out, True


def sharpen(im, scale):
    # nitidez después de reducir; más suave si se redujo mucho
    return im.filter(ImageFilter.UnsharpMask(radius=0.8 if scale < 0.5 else 1.0, percent=70, threshold=2))


def crop45(im, cx=0.5):
    W, H = im.size
    if W / H > IG_W / IG_H:
        w = int(H * IG_W / IG_H); x = int(min(max(0, cx * W - w / 2), W - w))
        return im.crop((x, 0, x + w, H))
    h = int(W * IG_H / IG_W); y = (H - h) // 2
    return im.crop((0, y, W, y + h))


def save(im, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    im.save(path, quality=92, subsampling=0, optimize=True, progressive=True)


def main(src, dst, args):
    ig = "--ig" in args
    pairs = [a for a in args if a != "--ig"]
    if not pairs:
        pairs = [f"{f}:{f}" for f in sorted(os.listdir(src)) if f.lower().endswith((".jpg", ".jpeg"))]
    for p in pairs:
        a, b = p.split(":", 1)
        cx = 0.5
        if "@" in b:
            b, cx = b.split("@"); cx = float(cx)
        orig = ImageOps.exif_transpose(Image.open(os.path.join(src, a))).convert("RGB")
        fixed, ok = correct(orig)
        # blog
        blog = fixed.copy(); blog.thumbnail((BLOG_MAX, BLOG_MAX), Image.LANCZOS)
        save(sharpen(blog, blog.width / fixed.width), os.path.join(dst, b))
        msg = f"{b}: {'corregida' if ok else 'ORIGINAL (la corrección quemaba luces)'}  quemado {clipped(blog)*100:.1f}%"
        # Instagram 4:5 desde resolución completa
        if ig:
            c = crop45(fixed, cx)
            if c.width < IG_W:
                msg += f"  ⚠ recorte de {c.width}px < 1080: se vería suave, elegir otra foto o recorte"
            c = c.resize((IG_W, IG_H), Image.LANCZOS) if c.width >= IG_W else c.resize((IG_W, IG_H), Image.BICUBIC)
            save(sharpen(c, IG_W / max(1, fixed.width)), os.path.join(dst, "ig", b))
        print(msg)


if __name__ == "__main__":
    if len(sys.argv) < 3: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
