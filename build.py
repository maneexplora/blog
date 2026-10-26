#!/usr/bin/env python3
"""Generador del sitio Mane Explora: content/*.md -> dist/ (HTML estático)."""
import glob, html, json, os, shutil, datetime, urllib.parse
import markdown, yaml

SITE = {
    "name": "Mane Explora",
    "url": "https://maneexplora.com",
    "tagline": "Reseñas honestas de restaurantes, cafés, cultura y viajes",
    "desc": "Lo bueno, lo mejorable y si vale la pena ir. Reseñas honestas de restaurantes, cafés, museos y viajes por Manuel Alemán.",
    "instagram": "maneexplora",
    "pinterest": "maneexplora",
    "adsense_client": "",  # ej. "ca-pub-1234567890" cuando AdSense apruebe el sitio
}
ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
MONTHS = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]

def esc(s): return html.escape(str(s or ""), quote=True)
def fdate(d): return f"{d.day} de {MONTHS[d.month-1]} de {d.year}"

def stars(r, num=True):
    if r in (None, ""): return ""
    r = float(r)
    return f'<span class="stars5" style="--p:{r/5*100:.0f}%" role="img" aria-label="{r:g} de 5 estrellas"></span>' + (f' <b>{r:g}/5</b>' if num else "")

WEIGHTS = {"Servicio": .35, "Sabor": .30, "Ambiente": .15, "Calidad-precio": .20,
           "Exposición": .35, "Experiencia y montaje": .20, "Edificio": .15, "Atención y orientación": .15}
MUSEUM_KEYS = {"Exposición", "Experiencia y montaje", "Edificio", "Atención y orientación"}

def weighted(sc):
    museum = bool(MUSEUM_KEYS & set(sc))
    w = {k: (WEIGHTS[k] if not (museum and k == "Calidad-precio") else .15) for k in sc}
    raw = sum(sc[k] * w[k] for k in sc)
    return raw, int(raw * 2 + 0.5 + 1e-9) / 2, w

def verdict(r):
    return "Vale el viaje" if r >= 4.5 else ("Vale el desvío" if r >= 3.5 else "Interesante")

def load():
    posts = []
    for f in glob.glob(os.path.join(ROOT, "content/resenas/*.md")):
        raw = open(f, encoding="utf-8").read()
        _, fm, body = raw.split("---", 2)
        meta = yaml.safe_load(fm)
        meta["html"] = markdown.markdown(body, extensions=["extra"])
        if meta.get("scores"): meta["rating"] = weighted(meta["scores"])[1]
        posts.append(meta)
    return sorted(posts, key=lambda p: p["date"], reverse=True)

ADS_HEAD = lambda: (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={SITE["adsense_client"]}" crossorigin="anonymous"></script>' if SITE["adsense_client"] else "")
AD_SLOT = lambda: ('<div class="ad"><ins class="adsbygoogle" style="display:block" data-ad-format="auto" data-full-width-responsive="true" data-ad-client="%s"></ins><script>(adsbygoogle=window.adsbygoogle||[]).push({});</script></div>' % SITE["adsense_client"] if SITE["adsense_client"] else "")

def page(title, desc, body, path, image=None, jsonld=None):
    url = SITE["url"] + path
    img = SITE["url"] + (image or "/img/og.jpg")
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
    return f"""<!doctype html>
<html lang="es"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{img}"><meta property="og:url" content="{url}"><meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<link rel="alternate" type="application/rss+xml" title="{SITE['name']}" href="/rss.xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Inter:wght@400;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/style.css">{ADS_HEAD()}{ld}
</head><body>
<header class="top"><a class="logo" href="/">Mane <span>Explora</span></a>
<nav><a href="/">Reseñas</a><a href="/sobre-mi/">Sobre mí</a><a href="https://www.instagram.com/{SITE['instagram']}" rel="noopener">Instagram</a></nav></header>
<main>{body}</main>
<footer><p>© {datetime.date.today().year} {SITE['name']} · Reseñas honestas, sin patrocinios ocultos.</p>
<p><a href="/sobre-mi/">Sobre mí</a> · <a href="/privacidad/">Privacidad</a> · <a href="/rss.xml">RSS</a> · <a href="https://www.instagram.com/{SITE['instagram']}">Instagram</a> · <a href="https://www.pinterest.com/{SITE['pinterest']}">Pinterest</a></p></footer>
</body></html>"""

SECTIONS = [("restaurantes", "Restaurantes y cafés", lambda p: "Arte" not in p["category"]), ("arte-y-cultura", "Arte y cultura", lambda p: "Arte" in p["category"])]
def chips(active=None):
    return '<nav class="chips"><a href="/"' + (' class="on"' if not active else '') + '>Todas</a>' + "".join(f'<a href="/categoria/{k}/"' + (' class="on"' if k == active else '') + f'>{n}</a>' for k, n, _ in SECTIONS) + '</nav>'

def card(p):
    return f"""<a class="card" href="/resenas/{p['slug']}/"><img src="{p['cover']}" alt="{esc(p['place'])}" loading="lazy">
<div class="card-b"><span class="cat">{esc(p['category'])} · {esc(p['city'])}</span><h2>{esc(p['place'])}</h2>
<p>{esc(p['excerpt'])}</p><div class="meta">{stars(p.get('rating'))}</div></div></a>"""

def review(p):
    q = urllib.parse.quote(p["map_query"])
    gal = "".join(f'<figure><img src="{g[0]}" alt="{esc(g[1])}" loading="lazy"><figcaption>{esc(g[1])}</figcaption></figure>' for g in p["gallery"][1:])
    ig = f' · <a href="https://www.instagram.com/{p["instagram"]}" rel="noopener">@{esc(p["instagram"])}</a>' if p.get("instagram") else ""
    sc = p.get("scores") or {}
    rating = ""
    scorecard = ""
    if sc:
        raw, final, w = weighted(sc)
        p["rating"] = final
        label = p.get("verdict_label") and verdict(final)
        rows = "".join(f'<tr><td>{esc(k)}</td><td class="num">{w[k]*100:.0f}%</td><td><div class="bar"><i style="width:{v/5*100:.0f}%"></i></div></td><td class="num"><b>{v:g}</b></td></tr>' for k, v in sc.items())
        scorecard = (f'<section class="scorecard"><div class="sc-total"><div class="big">{final:g}</div>{stars(final, False)}<small>de 5</small>'
                     + (f'<span class="label">{label}</span>' if label else "") + '</div>'
                     + f'<table class="sc-table"><thead><tr><th>Criterio</th><th class="num">Peso</th><th>Calificación</th><th class="num">/5</th></tr></thead><tbody>{rows}</tbody>'
                     + f'<tfoot><tr><td colspan="4">Promedio ponderado: {raw:.2f} → {final:g} (redondeo a medio punto). <a href="/sobre-mi/#metodo">Ver método</a></td></tr></tfoot></table></section>')
    if p.get("rating") not in (None, ""):
        rating = f'<div class="rating">{stars(p["rating"])}</div>'
    facts = [("Gasto aprox. por persona", p.get("price_pp")), ("Reservación", p.get("reservation")), ("Tiempo de visita", p.get("duration")), ("Ideal para", p.get("ideal_for")),
             ("¿Volvería?", p.get("would_return")), ("Fecha de visita", fdate(p["date"]))]
    ficha = '<section class="ficha"><h2>Ficha rápida</h2><table>' + "".join(f"<tr><th>{k}</th><td>{esc(v)}</td></tr>" for k, v in facts if v) + "</table></section>"
    order = "".join(f"<li>{esc(x)}</li>" for x in (p.get("order") or []))
    avoid = "".join(f"<li>{esc(x)}</li>" for x in (p.get("avoid") or []))
    tips = ""
    if order or avoid:
        tips = '<div class="tips">' + (f'<div class="tip ok"><h3>{esc(p.get("order_title","Qué pedir"))}</h3><ul>{order}</ul></div>' if order else "") + (f'<div class="tip no"><h3>{esc(p.get("avoid_title","Qué evitaría"))}</h3><ul>{avoid}</ul></div>' if avoid else "") + "</div>"
    disclosure = '<p class="disclosure">Transparencia: esta visita la pagué al 100%. Sin invitación ni patrocinio.</p>' if p.get("paid") else ""
    author = '<div class="author"><img src="/img/manuel-avatar.jpg" alt="Manuel Alemán" loading="lazy"><p><b>Manuel Alemán</b><br>Supply Chain global de profesión, explorador por gusto. Reseño cada lugar con el mismo método y la misma escala. <a href="/sobre-mi/">Conoce mi método →</a></p></div>'
    ld = {"@context":"https://schema.org","@type":"Review","name":p["title"],"datePublished":str(p["date"]),
          "author":{"@type":"Person","name":"Manuel Alemán"},"publisher":{"@type":"Organization","name":SITE["name"]},
          "itemReviewed":{"@type":"Restaurant" if "Restaurante" in p["category"] or "Cafetería" in p["category"] else "Museum","name":p["place"],"address":p["city"]},
          "description":p["excerpt"],"image":SITE["url"]+p["cover"]}
    if p.get("rating") not in (None, ""): ld["reviewRating"]={"@type":"Rating","ratingValue":p["rating"],"bestRating":5,"worstRating":1}
    body = f"""<article class="review">
<p class="cat">{esc(p['category'])} · {esc(p['city'])}</p>
<h1>{esc(p['title'])}</h1>
<p class="byline">Por Manuel Alemán · {fdate(p['date'])}{ig}</p>
{rating}
<figure class="hero"><img src="{p['cover']}" alt="{esc(p['gallery'][0][1])}"><figcaption>{esc(p['gallery'][0][1])}</figcaption></figure>
{scorecard}
{ficha}
<div class="prose">{p['html']}</div>
{tips}
{disclosure}
{AD_SLOT()}
<h2>Galería</h2><div class="gallery">{gal}</div>
<h2>Cómo llegar y qué opina la gente</h2>
<div class="map"><iframe title="Mapa de {esc(p['place'])}" src="https://www.google.com/maps?q={q}&output=embed" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe></div>
<p class="links"><a class="btn" href="https://www.google.com/maps/search/?api=1&query={q}" rel="noopener">Ver todas las reseñas en Google Maps ↗</a></p>
{author}
</article>"""
    return page(f"{p['title']} | {SITE['name']}", p["excerpt"], body, f"/resenas/{p['slug']}/", p["cover"], ld)

def static_page(slug, title, md):
    return page(f"{title} | {SITE['name']}", SITE["desc"], f'<article class="review"><h1>{esc(title)}</h1><div class="prose">{markdown.markdown(md, extensions=["extra"])}</div></article>', f"/{slug}/")

def write(path, txt):
    full = os.path.join(DIST, path.lstrip("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(txt)

def main():
    shutil.rmtree(DIST, ignore_errors=True)
    shutil.copytree(os.path.join(ROOT, "static"), DIST)
    posts = load()
    hero = f"""<section class="intro"><h1>{SITE['tagline']}</h1><p>Lo bueno, lo mejorable y si vale la pena ir. Sin filtros ni patrocinios ocultos.</p></section>"""
    write("index.html", page(f"{SITE['name']} · {SITE['tagline']}", SITE["desc"], hero + chips() + '<section class="grid">' + "".join(card(p) for p in posts) + "</section>", "/", posts[0]["cover"] if posts else None,
        {"@context":"https://schema.org","@type":"WebSite","name":SITE["name"],"url":SITE["url"]}))
    for p in posts: write(f"resenas/{p['slug']}/index.html", review(p))
    for k, n, f in SECTIONS:
        sel = [p for p in posts if f(p)]
        write(f"categoria/{k}/index.html", page(f"{n} | {SITE['name']}", f"Reseñas honestas de {n.lower()}.", f'<section class="intro"><h1>{n}</h1></section>' + chips(k) + '<section class="grid">' + "".join(card(p) for p in sel) + "</section>", f"/categoria/{k}/"))
    for slug, title in [("sobre-mi","Sobre mí"),("privacidad","Política de privacidad")]:
        write(f"{slug}/index.html", static_page(slug, title, open(os.path.join(ROOT, f"content/{slug}.md"), encoding="utf-8").read()))
    write("404.html", page(f"Página no encontrada | {SITE['name']}", SITE["desc"], '<section class="intro"><h1>Esta página no existe</h1><p><a href="/">Volver a las reseñas</a></p></section>', "/404"))
    # RSS
    items = "".join(f"<item><title>{esc(p['title'])}</title><link>{SITE['url']}/resenas/{p['slug']}/</link><guid>{SITE['url']}/resenas/{p['slug']}/</guid><pubDate>{datetime.datetime.combine(p['date'], datetime.time(10)).strftime('%a, %d %b %Y %H:%M:%S -0600')}</pubDate><description>{esc(p['excerpt'])}</description><enclosure url=\"{SITE['url']}{p['cover']}\" type=\"image/jpeg\" length=\"0\"/></item>" for p in posts)
    write("rss.xml", f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{SITE["name"]}</title><link>{SITE["url"]}</link><description>{esc(SITE["desc"])}</description><language>es</language>{items}</channel></rss>')
    urls = ["/", "/sobre-mi/", "/privacidad/"] + [f"/categoria/{k}/" for k, _, _ in SECTIONS] + [f"/resenas/{p['slug']}/" for p in posts]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(f"<url><loc>{SITE['url']}{u}</loc></url>" for u in urls) + "</urlset>")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE['url']}/sitemap.xml\n")
    print(f"OK: {len(posts)} reseñas -> dist/")

if __name__ == "__main__": main()
