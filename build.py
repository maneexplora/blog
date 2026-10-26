#!/usr/bin/env python3
"""Generador del sitio Mane Explora: content/*.md -> dist/ (HTML estático, ES / EN / 中文).

Español es el idioma base (raíz del sitio). Las traducciones viven en content/i18n/<lang>/:
  resenas/<slug>.md  -> sobrescribe campos de texto del frontmatter + cuerpo (captions = pies de la galería, en orden)
  about.md, privacy.md
Si una reseña no tiene traducción, no se publica en ese idioma (nunca se muestra texto a medias).
"""
import glob, html, json, os, re, shutil, datetime, urllib.parse
import markdown, yaml

SITE = {
    "name": "Mane Explora",
    "url": "https://maneexplora.com",
    "instagram": "maneexplora",
    "pinterest": "maneexplora",
    "adsense_client": "",  # ej. "ca-pub-1234567890" cuando AdSense apruebe el sitio
}
ROOT = os.path.dirname(os.path.abspath(__file__))
import hashlib
CSS_V = hashlib.md5(open(os.path.join(ROOT, "static/style.css"), "rb").read()).hexdigest()[:8]  # cambia con cada cambio de diseño
DIST = os.path.join(ROOT, "dist")
LANGS = ["es", "en", "zh"]
HTML_LANG = {"es": "es", "en": "en", "zh": "zh-Hans"}
OG_LOCALE = {"es": "es_MX", "en": "en_US", "zh": "zh_CN"}
LANG_LABEL = {"es": "ES", "en": "EN", "zh": "中文"}
LANG_NAME = {"es": "Español", "en": "English", "zh": "简体中文"}

# ---------- Textos de la interfaz ----------
T = {
 "es": dict(
    tagline="Reseñas honestas de restaurantes, cafés, cultura y viajes",
    desc="Lo bueno, lo mejorable y si vale la pena ir. Reseñas honestas de restaurantes, cafés, museos y viajes por Manuel Alemán.",
    intro="Lo bueno, lo mejorable y si vale la pena ir. Sin filtros ni patrocinios ocultos.",
    nav_reviews="Reseñas", nav_about="Sobre mí", all="Todas", privacy="Privacidad",
    about_title="Sobre mí", privacy_title="Política de privacidad",
    sections={"restaurantes": "Restaurantes y cafés", "arte-y-cultura": "Arte y cultura"},
    section_desc="Reseñas honestas de {n}.",
    of5="de 5 · calificación general", criterion="Criterio", weight="Peso", score="Calificación",
    wnote="Promedio ponderado: {raw} → {final}, redondeado a medio punto.", method="Ver mi método",
    facts="Ficha rápida", f_price="Gasto aprox. por persona", f_res="Reservación", f_dur="Tiempo de visita",
    f_ideal="Ideal para", f_ret="¿Volvería?", f_date="Fecha de visita",
    order="Qué pedir", avoid="Qué evitaría",
    disclosure="Transparencia: esta visita la pagué al 100%. Sin invitación ni patrocinio.",
    gallery="Galería", map_h="Cómo llegar y qué opina la gente", map_title="Mapa de {p}",
    map_btn="Ver todas las reseñas en Google Maps ↗", by="Por Manuel Alemán · {d}",
    author="Supply Chain global de profesión, explorador por gusto. Reseño cada lugar con el mismo método y la misma escala.",
    author_link="Conoce mi método →", stars_aria="{r} de 5 estrellas",
    footer="Reseñas honestas, sin patrocinios ocultos.", nf_title="Página no encontrada",
    nf_h="Esta página no existe", nf_back="Volver a las reseñas", lang_label="Idioma",
    verdicts=("Vale el viaje", "Vale el desvío", "Interesante"),
    crit={}),
 "en": dict(
    tagline="Honest reviews of restaurants, cafés, culture and travel",
    desc="The good, what could be better, and whether it's worth going. Honest reviews of restaurants, cafés, museums and travel by Manuel Alemán.",
    intro="The good, what could be better, and whether it's worth going. No filters, no hidden sponsorships.",
    nav_reviews="Reviews", nav_about="About me", all="All", privacy="Privacy",
    about_title="About me", privacy_title="Privacy policy",
    sections={"restaurantes": "Restaurants & cafés", "arte-y-cultura": "Art & culture"},
    section_desc="Honest reviews: {n}.",
    of5="out of 5 · overall rating", criterion="Criterion", weight="Weight", score="Rating",
    wnote="Weighted average: {raw} → {final}, rounded to the nearest half point.", method="See my method",
    facts="Quick facts", f_price="Approx. spend per person", f_res="Reservation", f_dur="Visit length",
    f_ideal="Ideal for", f_ret="Would I return?", f_date="Date of visit",
    order="What to order", avoid="What I'd skip",
    disclosure="Transparency: I paid for this visit in full. No invitation or sponsorship.",
    gallery="Gallery", map_h="Getting there and what people say", map_title="Map of {p}",
    map_btn="See all reviews on Google Maps ↗", by="By Manuel Alemán · {d}",
    author="Global Supply Chain professional by trade, explorer by choice. I review every place with the same method and the same scale.",
    author_link="See my method →", stars_aria="{r} out of 5 stars",
    footer="Honest reviews, no hidden sponsorships.", nf_title="Page not found",
    nf_h="This page doesn't exist", nf_back="Back to the reviews", lang_label="Language",
    verdicts=("Worth the trip", "Worth a detour", "Interesting"),
    crit={"Servicio": "Service", "Sabor": "Flavor", "Ambiente": "Ambience", "Calidad-precio": "Value for money",
          "Exposición": "Exhibition", "Experiencia y montaje": "Experience & curation", "Edificio": "Building",
          "Atención y orientación": "Guidance & assistance"}),
 "zh": dict(
    tagline="餐厅、咖啡馆、文化与旅行的真实点评",
    desc="好在哪里、哪里还能更好、值不值得去。Manuel Alemán 关于餐厅、咖啡馆、博物馆与旅行的真实点评。",
    intro="好在哪里、哪里还能更好、值不值得去。不加滤镜，没有隐藏赞助。",
    nav_reviews="点评", nav_about="关于我", all="全部", privacy="隐私政策",
    about_title="关于我", privacy_title="隐私政策",
    sections={"restaurantes": "餐厅与咖啡馆", "arte-y-cultura": "艺术与文化"},
    section_desc="真实点评：{n}。",
    of5="满分 5 分 · 综合评分", criterion="标准", weight="权重", score="评分",
    wnote="加权平均：{raw} → {final}（四舍五入至 0.5 分）。", method="查看我的评分方法",
    facts="速览", f_price="人均消费（约）", f_res="是否需要预订", f_dur="参观时长",
    f_ideal="适合", f_ret="会再去吗？", f_date="到访日期",
    order="推荐点什么", avoid="我会避开的",
    disclosure="透明声明：此次消费由我全额自费，无邀请、无赞助。",
    gallery="图集", map_h="如何前往及大众评价", map_title="{p} 地图",
    map_btn="在 Google 地图查看全部评价 ↗", by="作者：Manuel Alemán · {d}",
    author="职业是全球供应链，爱好是探索。每个地方我都用同样的方法和同样的评分标准来点评。",
    author_link="了解我的评分方法 →", stars_aria="{r} 星（满分 5 星）",
    footer="真实点评，绝无隐藏赞助。", nf_title="页面不存在",
    nf_h="此页面不存在", nf_back="返回点评", lang_label="语言",
    verdicts=("值得专程前往", "值得绕道前往", "有意思"),
    crit={"Servicio": "服务", "Sabor": "口味", "Ambiente": "环境", "Calidad-precio": "性价比",
          "Exposición": "展览", "Experiencia y montaje": "体验与布展", "Edificio": "建筑",
          "Atención y orientación": "服务与导览"}),
}
MONTHS = {"es": ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"],
          "en": ["January","February","March","April","May","June","July","August","September","October","November","December"]}

def fdate(d, lang):
    if lang == "en": return f"{MONTHS['en'][d.month-1]} {d.day}, {d.year}"
    if lang == "zh": return f"{d.year}年{d.month}月{d.day}日"
    return f"{d.day} de {MONTHS['es'][d.month-1]} de {d.year}"

# ---------- Rutas por idioma ----------
SEG = {"es": dict(rev="resenas", cat="categoria", about="sobre-mi", privacy="privacidad"),
       "en": dict(rev="reviews", cat="category", about="about", privacy="privacy"),
       "zh": dict(rev="reviews", cat="category", about="about", privacy="privacy")}
CAT_SLUG = {"es": {"restaurantes": "restaurantes", "arte-y-cultura": "arte-y-cultura"},
            "en": {"restaurantes": "restaurants", "arte-y-cultura": "art-and-culture"},
            "zh": {"restaurantes": "restaurants", "arte-y-cultura": "art-and-culture"}}

def url(lang, kind, key=None):
    pre = "" if lang == "es" else f"/{lang}"
    s = SEG[lang]
    if kind == "home": return pre + "/"
    if kind == "rev": return f"{pre}/{s['rev']}/{key}/"
    if kind == "cat": return f"{pre}/{s['cat']}/{CAT_SLUG[lang][key]}/"
    return f"{pre}/{s[kind]}/"

def esc(s): return html.escape(str(s or ""), quote=True)

def stars(r, lang, num=True):
    if r in (None, ""): return ""
    r = float(r)
    return f'<span class="stars5" style="--p:{r/5*100:.0f}%" role="img" aria-label="{esc(T[lang]["stars_aria"].format(r=f"{r:g}"))}"></span>' + (f' <b>{r:g}/5</b>' if num else "")

WEIGHTS = {"Servicio": .35, "Sabor": .30, "Ambiente": .15, "Calidad-precio": .20,
           "Exposición": .35, "Experiencia y montaje": .20, "Edificio": .15, "Atención y orientación": .15}
MUSEUM_KEYS = {"Exposición", "Experiencia y montaje", "Edificio", "Atención y orientación"}

def weighted(sc):
    museum = bool(MUSEUM_KEYS & set(sc))
    w = {k: (WEIGHTS[k] if not (museum and k == "Calidad-precio") else .15) for k in sc}
    raw = sum(sc[k] * w[k] for k in sc)
    return raw, int(raw * 2 + 0.5 + 1e-9) / 2, w

def verdict(r, lang):
    v = T[lang]["verdicts"]
    return v[0] if r >= 4.5 else (v[1] if r >= 3.5 else v[2])

def tables(h):
    """Da a las tablas de Markdown el estilo único del sitio."""
    def fix(m):
        head = m.group(1)
        return f'<table class="{"tbl wide" if head.count("<th") >= 4 else "tbl"}">' + head
    return re.sub(r"<table>(.*?</tr>)", fix, h, flags=re.S)

def md(text): return tables(markdown.markdown(text, extensions=["extra"]))

def parse(f):
    _, fm, body = open(f, encoding="utf-8").read().split("---", 2)
    return yaml.safe_load(fm) or {}, body

# ---------- Carga ----------
def load():
    posts = {l: [] for l in LANGS}
    for f in glob.glob(os.path.join(ROOT, "content/resenas/*.md")):
        base, body = parse(f)
        base["section"] = "arte-y-cultura" if "Arte" in base["category"] else "restaurantes"
        if base.get("scores"): base["rating"] = weighted(base["scores"])[1]
        base["langs"] = ["es"]
        variants = {"es": dict(base, html=md(body))}
        for l in LANGS[1:]:
            tf = os.path.join(ROOT, f"content/i18n/{l}/resenas/{base['slug']}.md")
            if not os.path.exists(tf): continue
            tr, tbody = parse(tf)
            v = dict(base); v.update({k: x for k, x in tr.items() if k != "captions"})
            caps = tr.get("captions") or []
            v["gallery"] = [[g[0], caps[i] if i < len(caps) else g[1]] for i, g in enumerate(base["gallery"])]
            v["html"] = md(tbody)
            variants[l] = v
        for l, v in variants.items():
            v["langs"] = list(variants)
            posts[l].append(v)
    for l in LANGS: posts[l].sort(key=lambda p: p["date"], reverse=True)
    return posts

# Analítica web de Metricool (sin cookies). Hash de la marca Mane Explora en Metricool.
METRICOOL = '<script>function loadScript(a){var b=document.getElementsByTagName("head")[0],c=document.createElement("script");c.type="text/javascript",c.src="https://tracker.metricool.com/resources/be.js",c.onreadystatechange=a,c.onload=a,b.appendChild(c)}loadScript(function(){beTracker.t({hash:"1a0a11f14e3e3431d40b49342240c54a"})});</script>'
ADS_HEAD = lambda: (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={SITE["adsense_client"]}" crossorigin="anonymous"></script>' if SITE["adsense_client"] else "")
AD_SLOT = lambda: ('<div class="ad"><ins class="adsbygoogle" style="display:block" data-ad-format="auto" data-full-width-responsive="true" data-ad-client="%s"></ins><script>(adsbygoogle=window.adsbygoogle||[]).push({});</script></div>' % SITE["adsense_client"] if SITE["adsense_client"] else "")

def page(lang, title, desc, body, alts, image=None, jsonld=None, nav=None):
    """alts: {lang: ruta} con las versiones equivalentes de esta página."""
    t = T[lang]
    path = alts[lang]
    img = SITE["url"] + (image or "/img/og.jpg")
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
    hreflang = "".join(f'<link rel="alternate" hreflang="{HTML_LANG[l]}" href="{SITE["url"]}{p}">' for l, p in alts.items())
    if "es" in alts: hreflang += f'<link rel="alternate" hreflang="x-default" href="{SITE["url"]}{alts["es"]}">'
    # En China las fuentes de Google no cargan: la versión en chino usa fuentes del sistema.
    fonts = "" if lang == "zh" else ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
             '<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Inter:wght@400;600&display=swap" rel="stylesheet">')
    switch = '<div class="lang" role="navigation" aria-label="' + esc(t["lang_label"]) + '">' + "".join(
        (f'<a href="{alts[l]}" hreflang="{HTML_LANG[l]}" lang="{HTML_LANG[l]}" title="{LANG_NAME[l]}"' + (' class="on" aria-current="true"' if l == lang else "") + f'>{LANG_LABEL[l]}</a>')
        if l in alts else f'<a href="{url(l, "home")}" hreflang="{HTML_LANG[l]}" lang="{HTML_LANG[l]}" title="{LANG_NAME[l]}">{LANG_LABEL[l]}</a>'
        for l in LANGS) + "</div>"
    home, about, priv = url(lang, "home"), url(lang, "about"), url(lang, "privacy")
    return f"""<!doctype html>
<html lang="{HTML_LANG[lang]}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITE['url']}{path}">{hreflang}
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{img}"><meta property="og:url" content="{SITE['url']}{path}"><meta property="og:type" content="website"><meta property="og:locale" content="{OG_LOCALE[lang]}">
<meta name="twitter:card" content="summary_large_image">
<link rel="alternate" type="application/rss+xml" title="{SITE['name']}" href="/rss.xml">
{fonts}
<link rel="stylesheet" href="/style.css?v={CSS_V}">{ADS_HEAD()}{ld}{METRICOOL}
</head><body>
<header class="top"><a class="logo" href="{home}">Mane <span>Explora</span></a>
<div class="top-r"><nav><a href="{home}">{t['nav_reviews']}</a><a href="{about}">{t['nav_about']}</a><a href="https://www.instagram.com/{SITE['instagram']}" rel="noopener">Instagram</a></nav>{switch}</div></header>
<main>{body}</main>
<footer><p>© {datetime.date.today().year} {SITE['name']} · {t['footer']}</p>
<p><a href="{about}">{t['nav_about']}</a> · <a href="{priv}">{t['privacy']}</a> · <a href="/rss.xml">RSS</a> · <a href="https://www.instagram.com/{SITE['instagram']}">Instagram</a> · <a href="https://www.pinterest.com/{SITE['pinterest']}">Pinterest</a></p></footer>
</body></html>"""

def chips(lang, active=None):
    t = T[lang]
    return '<nav class="chips"><a href="' + url(lang, "home") + '"' + (' class="on"' if not active else '') + f'>{t["all"]}</a>' + "".join(
        f'<a href="{url(lang, "cat", k)}"' + (' class="on"' if k == active else '') + f'>{n}</a>' for k, n in t["sections"].items()) + '</nav>'

def card(p, lang):
    return f"""<a class="card" href="{url(lang, 'rev', p['slug'])}"><img src="{p['cover']}" alt="{esc(p['place'])}" loading="lazy">
<div class="card-b"><span class="cat">{esc(p['category'])} · {esc(p['city'])}</span><h2>{esc(p['place'])}</h2>
<p>{esc(p['excerpt'])}</p><div class="meta">{stars(p.get('rating'), lang)}</div></div></a>"""

def review(p, lang):
    t = T[lang]
    q = urllib.parse.quote(p["map_query"])
    gal = "".join(f'<figure><img src="{g[0]}" alt="{esc(g[1])}" loading="lazy"><figcaption>{esc(g[1])}</figcaption></figure>' for g in p["gallery"][1:])
    ig = f' · <a href="https://www.instagram.com/{p["instagram"]}" rel="noopener">@{esc(p["instagram"])}</a>' if p.get("instagram") else ""
    sc = p.get("scores") or {}
    rating = scorecard = ""
    if sc:
        raw, final, w = weighted(sc)
        label = p.get("verdict_label") and verdict(final, lang)
        rows = "".join(f'<tr><td>{esc(t["crit"].get(k, k))}</td><td class="num">{w[k]*100:.0f}%</td><td class="score">{stars(v, lang, False)}<b>{v:g}/5</b></td></tr>' for k, v in sc.items())
        scorecard = (f'<section class="scorecard"><div class="sc-head"><div class="big">{final:g}</div><div>{stars(final, lang, False)}<div class="of">{t["of5"]}</div></div>'
                     + (f'<span class="label">{label}</span>' if label else "") + '</div>'
                     + f'<table class="tbl"><thead><tr><th>{t["criterion"]}</th><th class="num">{t["weight"]}</th><th>{t["score"]}</th></tr></thead><tbody>{rows}</tbody>'
                     + f'<tfoot><tr><td colspan="3">{t["wnote"].format(raw=f"{raw:.2f}", final=f"{final:g}")} <a href="{url(lang, "about")}#metodo">{t["method"]}</a></td></tr></tfoot></table></section>')
    if p.get("rating") not in (None, ""):
        rating = f'<div class="rating">{stars(p["rating"], lang)}</div>'
    facts = [(t["f_price"], p.get("price_pp")), (t["f_res"], p.get("reservation")), (t["f_dur"], p.get("duration")), (t["f_ideal"], p.get("ideal_for")),
             (t["f_ret"], p.get("would_return")), (t["f_date"], fdate(p["date"], lang))]
    ficha = f'<section class="ficha"><h2>{t["facts"]}</h2><table class="tbl">' + "".join(f'<tr><th scope="row">{k}</th><td>{esc(v)}</td></tr>' for k, v in facts if v) + "</table></section>"
    order = "".join(f"<li>{esc(x)}</li>" for x in (p.get("order") or []))
    avoid = "".join(f"<li>{esc(x)}</li>" for x in (p.get("avoid") or []))
    tips = ""
    if order or avoid:
        tips = '<div class="tips">' + (f'<div class="tip ok"><h3>{esc(p.get("order_title") or t["order"])}</h3><ul>{order}</ul></div>' if order else "") + (f'<div class="tip no"><h3>{esc(p.get("avoid_title") or t["avoid"])}</h3><ul>{avoid}</ul></div>' if avoid else "") + "</div>"
    disclosure = f'<p class="disclosure">{t["disclosure"]}</p>' if p.get("paid") else ""
    author = f'<div class="author"><img src="/img/manuel-avatar.jpg" alt="Manuel Alemán" loading="lazy"><p><b>Manuel Alemán</b><br>{t["author"]} <a href="{url(lang, "about")}">{t["author_link"]}</a></p></div>'
    # Google Maps no carga en China: en chino solo se deja el botón.
    mapbox = "" if lang == "zh" else f'<div class="map"><iframe title="{esc(t["map_title"].format(p=p["place"]))}" src="https://www.google.com/maps?q={q}&output=embed" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe></div>'
    ld = {"@context":"https://schema.org","@type":"Review","name":p["title"],"datePublished":str(p["date"]),"inLanguage":HTML_LANG[lang],
          "author":{"@type":"Person","name":"Manuel Alemán"},"publisher":{"@type":"Organization","name":SITE["name"]},
          "itemReviewed":{"@type":"Museum" if p["section"] == "arte-y-cultura" else "Restaurant","name":p["place"],"address":p["city"]},
          "description":p["excerpt"],"image":SITE["url"]+p["cover"]}
    if p.get("rating") not in (None, ""): ld["reviewRating"]={"@type":"Rating","ratingValue":p["rating"],"bestRating":5,"worstRating":1}
    body = f"""<article class="review">
<p class="cat">{esc(p['category'])} · {esc(p['city'])}</p>
<h1>{esc(p['title'])}</h1>
<p class="byline">{t['by'].format(d=fdate(p['date'], lang))}{ig}</p>
{rating}
<figure class="hero"><img src="{p['cover']}" alt="{esc(p['gallery'][0][1])}"><figcaption>{esc(p['gallery'][0][1])}</figcaption></figure>
{scorecard}
{ficha}
<div class="prose">{p['html']}</div>
{tips}
{disclosure}
{AD_SLOT()}
<h2>{t['gallery']}</h2><div class="gallery">{gal}</div>
<h2>{t['map_h']}</h2>
{mapbox}
<p class="links"><a class="btn" href="https://www.google.com/maps/search/?api=1&query={q}" rel="noopener">{t['map_btn']}</a></p>
{author}
</article>"""
    alts = {l: url(l, "rev", p["slug"]) for l in p["langs"]}
    return page(lang, f"{p['title']} | {SITE['name']}", p["excerpt"], body, alts, p["cover"], ld)

def write(path, txt):
    full = os.path.join(DIST, path.lstrip("/"))
    if full.endswith("/"): full += "index.html"
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(txt)

def main():
    shutil.rmtree(DIST, ignore_errors=True)
    shutil.copytree(os.path.join(ROOT, "static"), DIST)
    posts = load()
    sitemap = []
    for lang in LANGS:
        t, ps = T[lang], posts[lang]
        alts_of = lambda kind, key=None: {l: url(l, kind, key) for l in LANGS}
        hero = f'<section class="intro"><h1>{t["tagline"]}</h1><p>{t["intro"]}</p></section>'
        write(url(lang, "home"), page(lang, f"{SITE['name']} · {t['tagline']}", t["desc"], hero + chips(lang) + '<section class="grid">' + "".join(card(p, lang) for p in ps) + "</section>",
              alts_of("home"), ps[0]["cover"] if ps else None, {"@context":"https://schema.org","@type":"WebSite","name":SITE["name"],"url":SITE["url"],"inLanguage":HTML_LANG[lang]}))
        sitemap.append(url(lang, "home"))
        for p in ps:
            write(url(lang, "rev", p["slug"]), review(p, lang)); sitemap.append(url(lang, "rev", p["slug"]))
        for k, n in t["sections"].items():
            sel = [p for p in ps if p["section"] == k]
            write(url(lang, "cat", k), page(lang, f"{n} | {SITE['name']}", t["section_desc"].format(n=n.lower() if lang == "es" else n),
                  f'<section class="intro"><h1>{n}</h1></section>' + chips(lang, k) + '<section class="grid">' + "".join(card(p, lang) for p in sel) + "</section>", alts_of("cat", k)))
            sitemap.append(url(lang, "cat", k))
        for kind, src in [("about", "sobre-mi"), ("privacy", "privacidad")]:
            f = os.path.join(ROOT, f"content/{src}.md") if lang == "es" else os.path.join(ROOT, f"content/i18n/{lang}/{kind}.md")
            title = t[f"{kind}_title"]
            write(url(lang, kind), page(lang, f"{title} | {SITE['name']}", t["desc"], f'<article class="review"><h1>{esc(title)}</h1><div class="prose">{md(open(f, encoding="utf-8").read())}</div></article>', alts_of(kind)))
            sitemap.append(url(lang, kind))
    # 404 (multilingüe)
    t = T["es"]
    write("404.html", page("es", f"{t['nf_title']} | {SITE['name']}", t["desc"], '<section class="intro"><h1>Esta página no existe · This page doesn\'t exist · 此页面不存在</h1><p><a href="/">Volver a las reseñas</a> · <a href="/en/">Back to the reviews</a> · <a href="/zh/">返回点评</a></p></section>', {"es": "/"}))
    # RSS (español)
    items = "".join(f"<item><title>{esc(p['title'])}</title><link>{SITE['url']}{url('es','rev',p['slug'])}</link><guid>{SITE['url']}{url('es','rev',p['slug'])}</guid><pubDate>{datetime.datetime.combine(p['date'], datetime.time(10)).strftime('%a, %d %b %Y %H:%M:%S -0600')}</pubDate><description>{esc(p['excerpt'])}</description><enclosure url=\"{SITE['url']}{p['cover']}\" type=\"image/jpeg\" length=\"0\"/></item>" for p in posts["es"])
    write("rss.xml", f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{SITE["name"]}</title><link>{SITE["url"]}</link><description>{esc(T["es"]["desc"])}</description><language>es</language>{items}</channel></rss>')
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(f"<url><loc>{SITE['url']}{u}</loc></url>" for u in sitemap) + "</urlset>")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE['url']}/sitemap.xml\n")
    # Redirecciones de las rutas en español que alguien pudiera escribir en otro idioma
    write("_redirects", "/en/resenas/* /en/reviews/:splat 301\n/zh/resenas/* /zh/reviews/:splat 301\n/en/sobre-mi/ /en/about/ 301\n/zh/sobre-mi/ /zh/about/ 301\n")
    print("OK: " + ", ".join(f"{l}={len(posts[l])}" for l in LANGS) + " reseñas -> dist/")

if __name__ == "__main__": main()
