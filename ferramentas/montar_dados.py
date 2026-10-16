"""Preenche o bloco de dados do index.html (<script id="dados">) a partir dos dados dos perfumes.

Uso (na pasta do site):
  python3 -I ferramentas/montar_dados.py dados/perfumes.json dados/config.json <dd/mm/aaaa>

O primeiro argumento também pode ser uma pasta com um JSON por perfume (formato antigo,
exportado do painel do Claude). Imprime quantos perfumes ativos entraram no site.
"""
import glob, json, os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fonte, cfgp, data = sys.argv[1:4]

cfg = json.load(open(cfgp, encoding="utf-8")); cfg = cfg.get("data", cfg)
secoes = cfg.get("secoes") or ["Masculinos", "Femininos"]

if os.path.isdir(fonte):
    brutos = [json.load(open(f, encoding="utf-8")) for f in glob.glob(os.path.join(fonte, "**", "*.json"), recursive=True)]
else:
    brutos = json.load(open(fonte, encoding="utf-8"))
    if isinstance(brutos, dict):
        brutos = brutos.get("perfumes", list(brutos.values()))

docs = []
for d in brutos:
    d = d.get("data", d) if isinstance(d, dict) else {}
    if "secao" not in d or "vista" not in d or d.get("status", "ativo") != "ativo":
        continue
    docs.append(d)
docs.sort(key=lambda d: (secoes.index(d["secao"]) if d.get("secao") in secoes else 99, d.get("ordem", 0)))


def notas(d):
    n = d.get("notas") or {}
    if not isinstance(n, dict):
        return {}
    return {k: str(v).strip() for k, v in n.items() if k in ("topo", "coracao", "fundo", "todas") and str(v or "").strip()}


prods = []
for d in docs:
    p = {"secao": d["secao"], "marca": d.get("marca", ""), "nome": d.get("nome", ""), "tipo": d.get("tipo", ""),
         "ml": d.get("ml"), "vista": d["vista"], "parcelado": d["parcelado"],
         "img": ("img/" + d["foto"] + ".jpg") if d.get("foto") else ""}
    ac = [str(a).strip() for a in (d.get("acordes") or []) if str(a).strip()]
    if ac:
        p["acordes"] = ac[:10]
    nt = notas(d)
    if nt:
        p["notas"] = nt
    if d.get("perfil_fonte"):
        p["fonte"] = d["perfil_fonte"]
    prods.append(p)

payload = json.dumps({"atualizado_em": data, "parcelas": cfg.get("parcelas", 6), "secoes": secoes, "produtos": prods},
                     ensure_ascii=False).replace("</", "<\\/")
page = os.path.join(BASE, "index.html")
html = open(page, encoding="utf-8").read()
new, n = re.subn(r'(<script id="dados" type="application/json">)(.*?)(</script>)',
                 lambda m: m.group(1) + payload + m.group(3), html, count=1, flags=re.S)
assert n == 1, "bloco de dados não encontrado"
open(page, "w", encoding="utf-8").write(new)
print(len(prods))
