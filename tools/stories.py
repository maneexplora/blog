#!/usr/bin/env python3
"""Genera las historias de Instagram (1080x1920) de cada reseña, ya editadas.

Uso:  python3 tools/stories.py [slug ...]      (sin argumentos: todas las reseñas con `stories:`)
Salida: static/stories/<slug>/<n>.jpg  -> se publican en https://maneexplora.com/stories/<slug>/<n>.jpg
        Metricool toma esas URLs como media de cada historia.

En el frontmatter de la reseña:
stories:
  - {photo: /img/lugar/foto.jpg, text: "Texto de la historia", sticker: mention}   # mention | poll | link | none
La tarjeta de calificación (rating.jpg) se genera sola a partir de `scores`.

Reglas de diseño (skill sección 7): 10% superior y franja inferior libres, texto blanco tipo máquina
de escribir, nada pegado a las orillas, espacio reservado donde va el sticker interactivo.
"""
import glob, os, sys
import yaml
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from build import weighted, verdict, T  # misma fórmula y textos que el blog

W, H = 1080, 1920
FONTS = os.path.join(ROOT, "tools", "fonts")
INTER = "/usr/share/fonts/opentype/inter/"
TYPE = os.path.join(FONTS, "CourierPrime-Bold.ttf")
STAR, STAR_OFF, ACCENT, CREAM = (217, 154, 30), (90, 82, 72), (233, 138, 79), (250, 247, 242)

def font(path, size, var=None):
    f = ImageFont.truetype(path, size)
    if var:
        try: f.set_variation_by_name(var)
        except Exception: pass
    return f

def inter(size, w="SemiBold"):
    p = os.path.join(INTER, f"Inter-{w}.otf")
    return ImageFont.truetype(p if os.path.exists(p) else TYPE, size)

def background(photo):
    """Fondo: la misma foto, desenfocada y oscurecida, llenando la pantalla."""
    bg = ImageOps.fit(photo, (W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(42))
    return Image.blend(bg, Image.new("RGB", (W, H), (12, 10, 8)), 0.55)

def rounded(img, r):
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, img.size[0] - 1, img.size[1] - 1], r, fill=255)
    out = img.copy(); out.putalpha(m); return out

def paste_card(canvas, photo, box):
    x0, y0, x1, y1 = box
    card = rounded(ImageOps.fit(photo, (x1 - x0, y1 - y0), Image.LANCZOS, centering=(0.5, 0.45)), 34)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([x0 + 6, y0 + 14, x1 + 6, y1 + 14], 34, fill=(0, 0, 0, 120))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18)))
    canvas.alpha_composite(card, (x0, y0))

def wrap(draw, text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=f) <= maxw: cur = t
        else: lines.append(cur); cur = w
    return lines + [cur]

def centered_text(draw, text, y, size, maxw=900, fill="white"):
    f = font(TYPE, size)
    lines = wrap(draw, text, f, maxw)
    while len(lines) > 3 and size > 40:
        size -= 4; f = font(TYPE, size); lines = wrap(draw, text, f, maxw)
    lh = int(size * 1.22)
    for i, ln in enumerate(lines):
        draw.text((W / 2, y + i * lh), ln, font=f, fill=fill, anchor="ma", stroke_width=2, stroke_fill=(0, 0, 0))
    return y + len(lines) * lh

def brand(draw, y):
    draw.text((W / 2, y), "MANE EXPLORA · RESEÑA HONESTA", font=inter(26, "SemiBold"), fill=(255, 255, 255, 200), anchor="ma")

def story(src, text, sticker):
    photo = Image.open(os.path.join(ROOT, "static", src.lstrip("/"))).convert("RGB")
    c = background(photo).convert("RGBA")
    d = ImageDraw.Draw(c)
    # Foto: deja libre el 10 % superior (nombre de la cuenta)
    card_h = 1000 if sticker != "none" else 1150
    paste_card(c, photo, (110, 230, 970, 230 + card_h))
    brand(d, 230 + card_h + 34)
    y = centered_text(d, text, 230 + card_h + 90, 60)
    # Debajo del texto queda el hueco para el sticker interactivo (encuesta, enlace o mención)
    # y la franja inferior (barra "Enviar mensaje") queda libre.
    return c.convert("RGB")

def star_shape(d, cx, cy, r, fill):
    import math
    pts = []
    for i in range(10):
        a = math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy - rr * math.sin(a)))
    d.polygon(pts, fill=fill)

def stars(c, x, y, r, value, gap):
    """5 estrellas con relleno parcial (medias estrellas)."""
    for i in range(5):
        cx = x + i * gap + r
        base = Image.new("RGBA", c.size, (0, 0, 0, 0)); bd = ImageDraw.Draw(base)
        star_shape(bd, cx, y + r, r, STAR_OFF)
        c.alpha_composite(base)
        frac = max(0, min(1, value - i))
        if frac > 0:
            on = Image.new("RGBA", c.size, (0, 0, 0, 0)); od = ImageDraw.Draw(on)
            star_shape(od, cx, y + r, r, STAR)
            mask = Image.new("L", c.size, 0)
            ImageDraw.Draw(mask).rectangle([cx - r, y, cx - r + 2 * r * frac, y + 2 * r], fill=255)
            c.paste(on, (0, 0), Image.composite(on.split()[3], Image.new("L", c.size, 0), mask))

def rating_card(p):
    """Tarjeta de calificación: no necesita sticker, se puede publicar en automático."""
    photo = Image.open(os.path.join(ROOT, "static", p["cover"].lstrip("/"))).convert("RGB")
    c = background(photo).convert("RGBA")
    d = ImageDraw.Draw(c)
    raw, final, w = weighted(p["scores"])
    panel = (90, 300, 990, 1560)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ov).rounded_rectangle(panel, 40, fill=(22, 19, 15, 228), outline=(255, 255, 255, 40), width=2)
    c.alpha_composite(ov)
    d.text((W / 2, 360), "RESEÑA HONESTA", font=inter(30, "SemiBold"), fill=ACCENT, anchor="ma")
    d.text((W / 2, 410), p["place"], font=font(os.path.join(FONTS, "Fraunces.ttf"), 76, "Bold"), fill=CREAM, anchor="ma")
    d.text((W / 2, 510), p["city"], font=inter(30, "Regular"), fill=(200, 192, 182), anchor="ma")
    d.text((W / 2, 580), f"{final:g}", font=font(os.path.join(FONTS, "Fraunces.ttf"), 190, "Bold"), fill=CREAM, anchor="ma")
    stars(c, W / 2 - 2.5 * 84 + 6, 800, 36, final, 84)
    label = verdict(final, "es") if p.get("verdict_label") else "de 5"
    d.text((W / 2, 890), label, font=inter(34, "SemiBold"), fill=ACCENT if p.get("verdict_label") else (200, 192, 182), anchor="ma")
    y = 980
    for k, v in p["scores"].items():
        d.line([(170, y - 22), (910, y - 22)], fill=(255, 255, 255, 50), width=2)
        d.text((170, y), k, font=inter(34, "Regular"), fill=CREAM, anchor="la")
        d.text((640, y + 2), f"{w[k]*100:.0f}%", font=inter(26, "Regular"), fill=(170, 162, 152), anchor="ra")
        stars(c, 690, y + 4, 16, v, 38)
        d.text((910, y), f"{v:g}", font=inter(34, "SemiBold"), fill=CREAM, anchor="ra")
        y += 92
    d.text((W / 2, 1490), "maneexplora.com", font=inter(32, "SemiBold"), fill=CREAM, anchor="ma")
    return c.convert("RGB")

def main(slugs):
    for f in sorted(glob.glob(os.path.join(ROOT, "content/resenas/*.md"))):
        _, fm, _ = open(f, encoding="utf-8").read().split("---", 2)
        p = yaml.safe_load(fm)
        if slugs and p["slug"] not in slugs: continue
        if not p.get("stories"): continue
        out = os.path.join(ROOT, "static", "stories", p["slug"]); os.makedirs(out, exist_ok=True)
        for i, s in enumerate(p["stories"], 1):
            story(s["photo"], s["text"], s.get("sticker", "none")).save(os.path.join(out, f"{i}.jpg"), quality=90)
        if p.get("scores"): rating_card(p).save(os.path.join(out, "rating.jpg"), quality=90)
        print(f"{p['slug']}: {len(p['stories'])} historias + tarjeta de calificación")

if __name__ == "__main__": main(sys.argv[1:])
