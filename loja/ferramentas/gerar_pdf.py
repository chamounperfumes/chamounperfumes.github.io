"""LOJA FÍSICA: gera loja/catalogo.pdf a partir dos dados de loja/index.html (bloco <script id="dados">) e das fotos em loja/img/.

Uso (na raiz do repositório):  python3 loja/ferramentas/gerar_pdf.py
Requer: reportlab e Pillow (pip install reportlab pillow).
"""
import io, json, math, os, re, sys

from PIL import Image
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTES = os.path.join(BASE, "ferramentas", "fontes")
pdfmetrics.registerFont(TTFont("Jakarta", os.path.join(FONTES, "PlusJakartaSans-Regular.ttf")))
pdfmetrics.registerFont(TTFont("Jakarta-Semi", os.path.join(FONTES, "PlusJakartaSans-SemiBold.ttf")))
pdfmetrics.registerFont(TTFont("Jakarta-Bold", os.path.join(FONTES, "PlusJakartaSans-ExtraBold.ttf")))

html = open(os.path.join(BASE, "index.html"), encoding="utf-8").read()
D = json.loads(re.search(r'<script id="dados" type="application/json">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))
N = int(D.get("parcelas") or 6)
secoes = D.get("secoes") or list(dict.fromkeys(p["secao"] for p in D["produtos"]))
OUTRAS = set(D.get("outras") or [])
LOJA = D.get("loja") or {}

INK, SOFT, FAINT, LINE = (0.07, 0.07, 0.07), (0.435, 0.435, 0.42), (0.59, 0.59, 0.565), (0.894, 0.894, 0.875)
W, H = 210 * mm, 297 * mm
M, GAP, COLS, FOOT = 10 * mm, 3.5 * mm, 4, 8 * mm
CW = (W - 2 * M - (COLS - 1) * GAP) / COLS
CH, PAD, IMGH = 63 * mm, 2.4 * mm, 28 * mm
IW = CW - 2 * PAD


def money(v):
    return f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def parcela(t):
    return math.floor(round(float(t) * 100) / N) / 100


_img = {}
def foto(rel, max_px=420):
    if rel in _img:
        return _img[rel]
    path = os.path.join(BASE, rel)
    if not rel or not os.path.exists(path):
        _img[rel] = None
        return None
    im = Image.open(path).convert("RGB")
    im.thumbnail((max_px, max_px))
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=82); buf.seek(0)
    _img[rel] = (ImageReader(buf), im.width, im.height)
    return _img[rel]


def fit(c, txt, font, size, maxw):
    if c.stringWidth(txt, font, size) <= maxw:
        return txt
    while len(txt) > 1 and c.stringWidth(txt + "…", font, size) > maxw:
        txt = txt[:-1]
    return txt.rstrip() + "…"


def wrap(c, txt, font, size, maxw, max_lines=2):
    words, lines, cur = txt.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if c.stringWidth(t, font, size) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines - 1] + [fit(c, " ".join(lines[max_lines - 1:]), font, size, maxw)]
    return [fit(c, l, font, size, maxw) for l in lines]


def main(out):
    c = canvas.Canvas(out, pagesize=(W, H))
    c.setTitle("Tabela Chamoun Perfumes · Loja"); c.setAuthor("Chamoun Perfumes Importados")
    y = M  # distância a partir do topo
    T = lambda yy: H - yy  # converte "do topo" para coordenada do reportlab

    logo_path = os.path.join(BASE, "img", "logo-preto.png")
    if os.path.exists(logo_path):
        lw = 64 * mm; li = Image.open(logo_path); lh = lw * li.height / li.width
        c.drawImage(ImageReader(logo_path), (W - lw) / 2, T(y + 2 * mm + lh), lw, lh, mask="auto")
        y += 2 * mm + lh + 5 * mm
    c.setFont("Jakarta", 8.5); c.setFillColorRGB(*SOFT)
    sub = "Loja física · Tabela de preços" + (" · atualizada em " + D["atualizado_em"] if D.get("atualizado_em") else "")
    c.drawCentredString(W / 2, T(y + 3 * mm), sub)
    y += 9 * mm
    if LOJA.get("endereco"):
        c.setFont("Jakarta-Semi", 8.5); c.setFillColorRGB(*INK)
        c.drawCentredString(W / 2, T(y + 1 * mm), fit(c, LOJA["endereco"], "Jakarta-Semi", 8.5, W - 2 * M))
        y += 7 * mm

    def nova_pagina():
        nonlocal y
        c.showPage(); y = M

    for s in secoes:
        ps = [p for p in D["produtos"] if p["secao"] == s]
        if not ps:
            continue
        if y + 14 * mm + CH > H - M - FOOT:
            nova_pagina()
        c.setFillColorRGB(*INK); c.roundRect(M, T(y + 14 * mm), W - 2 * M, 14 * mm, 3 * mm, stroke=0, fill=1)
        c.setFillColorRGB(0.65, 0.65, 0.63); c.setFont("Jakarta-Semi", 5.6)
        c.drawString(M + 5 * mm, T(y + 4.6 * mm), "P R O D U T O S" if s in OUTRAS else "P E R F U M E S")
        c.setFillColorRGB(1, 1, 1); c.setFont("Jakarta-Bold", 14)
        c.drawString(M + 5 * mm, T(y + 10.9 * mm), s.upper())
        c.setFont("Jakarta-Semi", 8)
        c.drawRightString(W - M - 5 * mm, T(y + 8 * mm), f"{len(ps)} {('produto' if s in OUTRAS else 'perfume') + ('' if len(ps) == 1 else 's')}")
        y += 14 * mm + GAP
        for i in range(0, len(ps), COLS):
            if y + CH > H - M - FOOT:
                nova_pagina()
            for col, p in enumerate(ps[i:i + COLS]):
                x = M + col * (CW + GAP)
                c.setStrokeColorRGB(*LINE); c.setFillColorRGB(1, 1, 1); c.setLineWidth(0.7)
                c.roundRect(x, T(y + CH), CW, CH, 3 * mm, stroke=1, fill=1)
                f = foto(p.get("img") or "")
                if f:
                    r, iw, ih = f
                    w = IW; h = IW * ih / iw
                    if h > IMGH:
                        h = IMGH; w = IMGH * iw / ih
                    c.drawImage(r, x + PAD + (IW - w) / 2, T(y + PAD + (IMGH - h) / 2 + h), w, h)
                ty = y + PAD + IMGH + 2.6 * mm
                c.setFillColorRGB(*FAINT); c.setFont("Jakarta-Semi", 5.6)
                c.drawString(x + PAD, T(ty + 2 * mm), fit(c, str(p.get("marca", "")).upper(), "Jakarta-Semi", 5.6, IW))
                ty += 2.9 * mm
                c.setFillColorRGB(*INK); c.setFont("Jakarta-Semi", 7.8)
                for k, ln in enumerate(wrap(c, str(p.get("nome", "")), "Jakarta-Semi", 7.8, IW)):
                    c.drawString(x + PAD, T(ty + 2.8 * mm + k * 3.3 * mm), ln)
                ty += 6.9 * mm
                meta = " · ".join(v for v in [f"{p['ml']} ml" if p.get("ml") else "", p.get("tipo") or ""] if v)
                c.setFillColorRGB(*SOFT); c.setFont("Jakarta", 6.4)
                c.drawString(x + PAD, T(ty + 2.3 * mm), fit(c, meta, "Jakarta", 6.4, IW))
                # Preços no pé do card
                py = y + CH - PAD - 11.2 * mm
                v = "R$ " + money(p["vista"])
                c.setFillColorRGB(*INK); c.setFont("Jakarta-Bold", 9.6); c.drawString(x + PAD, T(py + 3.3 * mm), v)
                vw = c.stringWidth(v, "Jakarta-Bold", 9.6)
                c.setFillColorRGB(*SOFT); c.setFont("Jakarta", 6.2); c.drawString(x + PAD + vw + 1.1 * mm, T(py + 3.3 * mm), "à vista")
                py += 4.3 * mm
                a = "R$ " + money(p["parcelado"])
                c.setFillColorRGB(*INK); c.setFont("Jakarta-Semi", 8.2); c.drawString(x + PAD, T(py + 2.9 * mm), a)
                aw = c.stringWidth(a, "Jakarta-Semi", 8.2)
                c.setFillColorRGB(*SOFT); c.setFont("Jakarta", 6.2); c.drawString(x + PAD + aw + 1.1 * mm, T(py + 2.9 * mm), "a prazo")
                py += 3.7 * mm
                pre = f"em até {N}x de "
                c.setFont("Jakarta", 6.2); c.drawString(x + PAD, T(py + 2.3 * mm), pre)
                pw = c.stringWidth(pre, "Jakarta", 6.2)
                c.setFillColorRGB(*INK); c.setFont("Jakarta-Semi", 6.2); c.drawString(x + PAD + pw, T(py + 2.3 * mm), "R$ " + money(parcela(p["parcelado"])))
            y += CH + GAP
        y += 3 * mm
    c.showPage()
    c.save()

    # Rodapé com número de página (segunda passada leve: reescreve com contagem total)
    from pypdf import PdfReader, PdfWriter
    rd = PdfReader(out); n = len(rd.pages); wr = PdfWriter()
    for i, page in enumerate(rd.pages, 1):
        buf = io.BytesIO(); fc = canvas.Canvas(buf, pagesize=(W, H))
        fc.setFont("Jakarta", 6.5); fc.setFillColorRGB(*FAINT)
        fc.drawString(M, 6 * mm, "chamounperfumes.github.io/loja")
        fc.drawRightString(W - M, 6 * mm, f"Página {i} de {n}")
        fc.save(); buf.seek(0)
        page.merge_page(PdfReader(buf).pages[0]); wr.add_page(page)
    wr.add_metadata({"/Title": "Tabela Chamoun Perfumes · Loja"})
    with open(out, "wb") as fh:
        wr.write(fh)
    print(f"{out}: {n} páginas, {len(D['produtos'])} produtos")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "catalogo.pdf"))
