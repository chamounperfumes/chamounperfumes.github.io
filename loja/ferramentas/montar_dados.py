"""Site da LOJA FÍSICA: preenche o bloco de dados de loja/index.html (<script id="dados">).

Uso (na raiz do repositório):
  python3 -I loja/ferramentas/montar_dados.py loja/dados/perfumes.json loja/dados/config.json <dd/mm/aaaa>

Diferenças para o site principal:
- Seções em config["outras"] são de outros produtos (sem notas e fora do assistente; volume opcional).
- config["loja"] (endereço, horário, WhatsApp, Instagram) vai junto para o site mostrar.
- Perfume sem acordes/notas reaproveita o perfil do mesmo perfume no catálogo principal
  (dados/perfumes.json na raiz), se existir lá.
Imprime quantos produtos ativos entraram no site.
"""
import json, os, re, sys, unicodedata

LOJA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # pasta loja/
RAIZ = os.path.dirname(LOJA)
fonte, cfgp, data = sys.argv[1:4]

cfg = json.load(open(cfgp, encoding="utf-8")); cfg = cfg.get("data", cfg)
secoes = cfg.get("secoes") or ["Masculinos", "Femininos"]
outras = [s for s in (cfg.get("outras") or []) if s in secoes]
loja = {k: str(v).strip() for k, v in (cfg.get("loja") or {}).items() if str(v or "").strip()}

brutos = json.load(open(fonte, encoding="utf-8"))
if isinstance(brutos, dict):
    brutos = brutos.get("perfumes", list(brutos.values()))


def chave(d):
    t = unicodedata.normalize("NFD", f'{d.get("marca", "")} {d.get("nome", "")}').encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


# Perfis do catálogo principal, para perfumes que a loja cadastrou sem notas.
perfis = {}
try:
    for d in json.load(open(os.path.join(RAIZ, "dados", "perfumes.json"), encoding="utf-8")):
        if d.get("acordes"):
            perfis.setdefault(chave(d), d)
except Exception:
    pass

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
         "ml": d.get("ml") or None, "vista": d["vista"], "parcelado": d["parcelado"],
         "img": ("img/" + d["foto"] + ".jpg") if d.get("foto") else ""}
    try:
        if d.get("parcelas"):
            p["parcelas"] = int(d["parcelas"])   # parcelas só deste produto (1 = sem parcelar)
    except (TypeError, ValueError):
        pass
    if d["secao"] not in outras:
        perfil = d
        if not [a for a in (d.get("acordes") or []) if str(a).strip()]:
            perfil = perfis.get(chave(d), d)
        ac = [str(a).strip() for a in (perfil.get("acordes") or []) if str(a).strip()]
        if ac:
            p["acordes"] = ac[:10]
        nt = notas(perfil)
        if nt:
            p["notas"] = nt
        if perfil.get("perfil_fonte"):
            p["fonte"] = perfil["perfil_fonte"]
    prods.append(p)

payload = json.dumps({"atualizado_em": data, "parcelas": cfg.get("parcelas", 6), "secoes": secoes, "outras": outras,
                      "loja": loja, "produtos": prods}, ensure_ascii=False).replace("</", "<\\/")
page = os.path.join(LOJA, "index.html")
html = open(page, encoding="utf-8").read()
new, n = re.subn(r'(<script id="dados" type="application/json">)(.*?)(</script>)',
                 lambda m: m.group(1) + payload + m.group(3), html, count=1, flags=re.S)
assert n == 1, "bloco de dados não encontrado"
open(page, "w", encoding="utf-8").write(new)
print(len(prods))
