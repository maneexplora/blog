#!/usr/bin/env python3
"""Guarda en la reseña el tipo de cambio del día para mostrar el precio en MXN, USD, CNY y EUR.

Uso:  python3 tools/fx.py <slug> [AAAA-MM-DD]     (sin fecha: tipos de cambio más recientes)

Requiere en el frontmatter:  price: {min: 25, max: 30, currency: EUR}   (max y approx: true son opcionales)
Escribe/actualiza:           fx: {date: ..., source: ..., rates: {MXN: ..., USD: ..., CNY: ..., EUR: ...}}

Fuente: Exchange API de fawazahmed0 (datos diarios abiertos), descargada del registro de npm
(paquete @fawazahmed0/currency-api, una versión por día). El tipo de cambio queda fijo en la reseña
con su fecha, para que la conversión sea reproducible y se pueda citar.
"""
import json, os, re, subprocess, sys, tarfile, tempfile
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = ["MXN", "USD", "CNY", "EUR"]
SOURCE = "Exchange API (fawazahmed0), datos diarios"

def rates_for(cur, date=None):
    ver = "latest" if not date else ".".join(str(int(x)) for x in date.split("-"))
    with tempfile.TemporaryDirectory() as d:
        out = subprocess.run(["npm", "pack", f"@fawazahmed0/currency-api@{ver}", "--silent"], cwd=d, capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1]
        with tarfile.open(os.path.join(d, out)) as t:
            f = t.extractfile(f"package/v1/currencies/{cur.lower()}.json")
            data = json.load(f)
    r = data[cur.lower()]
    return data["date"], {c: round(r[c.lower()], 6) for c in TARGETS if c != cur}

def main(slug, date=None):
    path = os.path.join(ROOT, "content", "resenas", f"{slug}.md")
    text = open(path, encoding="utf-8").read()
    _, fm, body = text.split("---", 2)
    meta = yaml.safe_load(fm)
    if not meta.get("price"): sys.exit("La reseña no tiene `price: {min, currency}`.")
    day, rates = rates_for(meta["price"]["currency"], date)
    line = "fx: " + json.dumps({"date": day, "source": SOURCE, "rates": rates}, ensure_ascii=False)
    if re.search(r"^fx:.*$", fm, flags=re.M): fm = re.sub(r"^fx:.*$", line, fm, flags=re.M)
    else: fm = re.sub(r"^(price:.*)$", r"\1\n" + line.replace("\\", "\\\\"), fm, count=1, flags=re.M)
    open(path, "w", encoding="utf-8").write("---" + fm + "---" + body)
    print(slug, day, rates)

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
