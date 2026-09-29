"""Radar de Leiloes de Veiculos - coleta diaria e gera pagina com os proximos 15 dias."""
import asyncio, json, re, pathlib, datetime, html, unicodedata
from urllib.parse import urlparse

HOJE = datetime.date.today()
LIMITE = HOJE + datetime.timedelta(days=15)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

UFS = {"AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR",
       "PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"}
CIDADE_UF = {"SAO PAULO": "SP", "RIO DE JANEIRO": "RJ", "CURITIBA": "PR", "BELO HORIZONTE": "MG",
             "PORTO ALEGRE": "RS", "FLORIANOPOLIS": "SC", "SALVADOR": "BA", "RECIFE": "PE",
             "FORTALEZA": "CE", "BELEM": "PA", "MANAUS": "AM", "BRASILIA": "DF", "GOIANIA": "GO",
             "VITORIA": "ES", "CAMPO GRANDE": "MS", "CUIABA": "MT", "FOZ DO IGUACU": "PR",
             "SANTOS": "SP", "CAMPINAS": "SP", "SOROCABA": "SP", "RIBEIRAO PRETO": "SP",
             "SAO JOSE DOS CAMPOS": "SP", "UBERLANDIA": "MG", "JUIZ DE FORA": "MG",
             "LONDRINA": "PR", "MARINGA": "PR", "CASCAVEL": "PR", "ITAJAI": "SC",
             "JOINVILLE": "SC", "NATAL": "RN", "JOAO PESSOA": "PB", "MACEIO": "AL",
             "ARACAJU": "SE", "TERESINA": "PI", "SAO LUIS": "MA", "PALMAS": "TO",
             "PORTO VELHO": "RO", "RIO BRANCO": "AC", "MACAPA": "AP", "BOA VISTA": "RR",
             "URUGUAIANA": "RS", "CORUMBA": "MS", "PONTA PORA": "MS", "GUAIRA": "PR"}

PALAVRAS_VEICULO = ["VEICUL", "CARRO", "MOTO", "CAMINH", "PESADO", "SUCATA", "UTILITAR",
                    "SEGURADORA", "AUTOMOV", "AUTOMOTOR", "FROTA", "ONIBUS", "RECUPERAD",
                    "PICK", "CAMIONET", "REBOQUE", "TRATOR", "VAN "]
PALAVRAS_NAO_VEICULO = ["IMOVE", "IMOVEI", "APARTAMENTO", "TERRENO", "CASA ", "GLEBA",
                        "FAZENDA", "CHACARA", "SALA COMERCIAL", "AERONAVE"]

# Organizadoras legitimas sem ficha unica na FENAJU (verificadas manualmente)
LISTA_CONFIAVEL = {"copart.com.br": "Organizadora nacional (Copart)",
                   "vipleiloes.com.br": "Organizadora nacional (VIP Leiloes)",
                   "loopleiloes.com.br": "Organizadora nacional (Loop / Webmotors)",
                   "superbid.net": "Plataforma nacional (Superbid Exchange)"}
EMAIL_GENERICO = {"gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "yahoo.com.br",
                  "uol.com.br", "bol.com.br", "terra.com.br", "icloud.com", "live.com",
                  "globo.com", "ig.com.br", "hotmail.com.br", "outlook.com.br", "msn.com"}


def sem_acento(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().upper()


def eh_veiculo(texto):
    t = sem_acento(texto)
    if any(p in t for p in PALAVRAS_NAO_VEICULO) and not any(p in t for p in ["VEICUL", "CARRO", "MOTO"]):
        return False
    return any(p in t for p in PALAVRAS_VEICULO)


def acha_uf(texto):
    t = sem_acento(texto)
    for m in re.finditer(r"(?:[-/(,]\s*|\s)([A-Z]{2})(?=\s*[)/]|\s*$|\s*-|\s*,)", t):
        if m.group(1) in UFS:
            return m.group(1)
    for cidade, uf in CIDADE_UF.items():
        if cidade in t:
            return uf
    return ""


def data_br(s, ano_padrao=None):
    m = re.search(r"(\d{1,2})/(\d{1,2})(?:/(\d{4}))?", s)
    if not m:
        return None
    d, mes, a = int(m.group(1)), int(m.group(2)), m.group(3)
    ano = int(a) if a else (ano_padrao or HOJE.year)
    try:
        dt = datetime.date(ano, mes, d)
    except ValueError:
        return None
    if not a and dt < HOJE - datetime.timedelta(days=60):
        dt = dt.replace(year=ano + 1)
    return dt


def hora_de(s):
    m = re.search(r"(\d{1,2})\s*[h:]\s*(\d{2})", s)
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else ""


def evento(data, nome, fonte, link, cidade="", uf="", hora="", obs=""):
    return {"data": data.isoformat() if data else "", "hora": hora, "nome": " ".join(nome.split()),
            "fonte": fonte, "link": link, "cidade": " ".join((cidade or "").split()),
            "uf": uf, "obs": obs}

# ---------------------------------------------------------------- parsers

def p_agenda_generica(cap, fonte, link, uf_padrao="", filtrar_veiculo=True):
    """Le agendas em texto: bloco que comeca numa data dd/mm/aaaa."""
    linhas = [l.strip() for l in cap["texto"].splitlines() if l.strip()]
    ignorar = {"EM BREVE", "ABERTO PARA LANCES", "FINALIZADO", "AO VIVO", "LOTES", "LOCATION_ON",
               "GAVEL", "VER LOTES", "VER LOTES AO VIVO", "EM PREGAO", "EM LOTEAMENTO",
               "ENCERRADO", "ABERTO PARA LANCE"}
    idx = [i for i, l in enumerate(linhas) if re.match(r"^\d{2}/\d{2}/\d{4}", l)]
    out = []
    for k, i in enumerate(idx):
        bloco = linhas[i + 1: idx[k + 1] if k + 1 < len(idx) else i + 12][:10]
        dt = data_br(linhas[i])
        local, titulo = "", ""
        for j, l in enumerate(bloco):
            u = sem_acento(l)
            if u in ignorar or re.fullmatch(r"\d+", l):
                continue
            if u == "LOCATION_ON" or (j > 0 and sem_acento(bloco[j - 1]) == "LOCATION_ON"):
                local = local or l
                continue
            if u.startswith("PATIO") or u.startswith("SOMENTE ONLINE") or u == "ONLINE":
                local = local or l
                continue
            if not titulo:
                titulo = l
        if not titulo or not dt:
            continue
        if filtrar_veiculo and not eh_veiculo(titulo):
            continue
        uf = acha_uf(local) or acha_uf(titulo) or uf_padrao
        out.append(evento(dt, titulo, fonte, link, local, uf, hora_de(linhas[i])))
    return out


def p_leilo(cap):
    return p_agenda_generica(cap, "Leilo", "https://leilo.com.br/agenda", "GO")


def p_freitas(cap):
    return p_agenda_generica(cap, "Freitas Leiloeiro", "https://www.freitasleiloeiro.com.br/Leiloes/Agenda", "SP")


def p_detran_mg(cap):
    out = []
    partes = re.split(r"Edital de Leil(?:ã|&atilde;)o<br>", cap["html"])[1:]
    for p in partes:
        num = re.match(r"\s*([\d/]+)", p)
        mun = re.search(r'capa-municipio">([^<]*)<', p)
        patio = re.search(r"<b>([^<]*)</b>", p)
        enc = re.search(r"Encerramento:\s*([\d/]+\s+[\d:]+)", p)
        lk = re.search(r'href="(/lotes/lista-lotes/[^"]+)"', p)
        status = "Finalizado" if "Finalizado" in p[:1500] else ""
        if not (num and enc) or status:
            continue
        cidade = html.unescape(mun.group(1)).title() if mun else ""
        link = "https://leilao.detran.mg.gov.br" + lk.group(1) if lk else "https://leilao.detran.mg.gov.br/"
        pt = html.unescape(patio.group(1)).strip() if patio else ""
        pt = re.sub(r"^\d+\s*-\s*", "", pt)
        nome = f"Detran-MG edital {num.group(1)} - patio {pt}"
        out.append(evento(data_br(enc.group(1)), nome, "Detran-MG", link, cidade, "MG",
                          hora_de(enc.group(1)), "Data = encerramento dos lances"))
    return out


def p_detran_rs(cap):
    out = []
    t = cap["texto"]
    for b in t.split("Edital EMAV:")[1:]:
        num = b.split("(")[0].strip()
        dt = re.search(r"Data do Leil[aã]o:\s*([\d/]+\s*[\d:]*)", b)
        loc = re.search(r"Local do Leil[aã]o:\s*(\S+)", b)
        cid = re.search(r"Cidade:\s*([^\n]+)", b)
        lei = re.search(r"Leiloeiro Oficial:\s*([^\n]+)", b)
        if not dt:
            continue
        link = loc.group(1) if loc and loc.group(1).startswith("http") else \
            "https://pcsdetran.rs.gov.br/consulta-calendario-leilao"
        nome = f"Detran-RS edital {num}" + (f" - leiloeiro {lei.group(1).strip()}" if lei else "")
        out.append(evento(data_br(dt.group(1)), nome, "Detran-RS", link,
                          cid.group(1).strip().title() if cid else "", "RS", hora_de(dt.group(1))))
    return out


def p_receita(cap):
    out = []
    for l in cap["texto"].splitlines():
        c = [x.strip() for x in l.split("\t")]
        if len(c) >= 5 and re.match(r"\d{7}/\d{7}/\d{4}", c[0]):
            edital, cidade = c[0].split(" ", 1) if " " in c[0] else (c[0], "")
            dt = data_br(c[3])
            out.append(evento(dt, f"Receita Federal edital {edital} ({c[4]} lotes)", "Receita Federal",
                              "https://www25.receita.fazenda.gov.br/sle-sociedade/portal",
                              cidade.title(), acha_uf(cidade), hora_de(c[3]),
                              f"Misto: verificar se ha veiculos. Propostas ate {c[2]}"))
    return out


def p_leiloesbrasil(cap):
    out = []
    for l in cap["texto"].splitlines():
        c = [x.strip() for x in l.split("\t")]
        if len(c) >= 6 and re.match(r"\d{2}/\d{2}", c[0]) and "VEICULO" in sem_acento(c[2]):
            if "COPART" in sem_acento(c[4]):
                continue  # ja coberto pela fonte Copart
            out.append(evento(data_br(c[0]), c[4], "Leiloes Brasil",
                              "https://www.leiloesbrasil.com.br/agenda", c[5] if "LINK" not in c[5] else "",
                              acha_uf(c[4] + " " + c[5]), hora_de(c[1]), c[3].title()))
    return out


def _json(cap, trecho):
    for a in cap["apis"]:
        if trecho in a["url"]:
            try:
                return json.loads(a["corpo"])
            except Exception:
                continue
    return None


def p_copart(cap):
    d = _json(cap, "auctionsCalendarList")
    out = []
    if not d:
        return out
    for s in d.get("data", {}).get("saleList", []):
        di = str(s.get("auctionDate", {}).get("dateAsInt", ""))
        if len(di) != 8:
            continue
        dt = datetime.date(int(di[:4]), int(di[4:6]), int(di[6:]))
        nome = f"Copart - {s.get('saleName', '')}"
        out.append(evento(dt, nome, "Copart", "https://www.copart.com.br/", s.get("saleName", "").split(" - ")[0],
                          acha_uf(s.get("saleName", "")), s.get("startTime", ""),
                          s.get("auctioneerName", "")))
    return out


def p_sodre(cap):
    out, vistos = [], set()
    for a in cap["apis"]:
        if "api/v1/auctions" not in a["url"]:
            continue
        try:
            d = json.loads(a["corpo"]).get("data", [])
        except Exception:
            continue
        for x in d:
            if x.get("id") in vistos:
                continue
            vistos.add(x.get("id"))
            segs = " ".join(s.get("name", "") for s in x.get("segments", []))
            if not eh_veiculo(segs + " " + x.get("name", "")):
                continue
            for dd in x.get("dates", []):
                v = dd.get("value", "")
                try:
                    dt = datetime.date.fromisoformat(v[:10])
                except ValueError:
                    continue
                out.append(evento(dt, f"Sodre Santoro - {x.get('name', '')}", "Sodre Santoro",
                                  "https://www.sodresantoro.com.br/veiculos/lotes",
                                  "Online" if not x.get("location") else x["location"], "", v[11:16],
                                  f"{x.get('quantity', '')} lotes"))
    return out


def p_parque(cap):
    d = _json(cap, "/eventos")
    out = []
    if not d:
        return out
    for dia, lista in (d.get("data") or {}).items():
        for e in lista:
            if eh_veiculo(e.get("type", "") + " " + e.get("name", "")):
                out.append(evento(datetime.date.fromisoformat(dia), e.get("name", ""), "Parque dos Leiloes",
                                  "https://www.parquedosleiloes.com.br/", "", ""))
    return out


FONTES = [
    ("Detran-MG", "https://leilao.detran.mg.gov.br/", p_detran_mg, []),
    ("Detran-RS", "https://pcsdetran.rs.gov.br/consulta-calendario-leilao", p_detran_rs, []),
    ("Receita Federal", "https://www25.receita.fazenda.gov.br/sle-sociedade/portal", p_receita, []),
    ("Copart", "https://www.copart.com.br/", p_copart, []),
    ("Sodre Santoro", "https://www.sodresantoro.com.br/", p_sodre,
     ["https://prd-api.sodresantoro.com.br/api/v1/auctions?limit=200"]),
    ("Leilo", "https://leilo.com.br/agenda", p_leilo, []),
    ("Freitas Leiloeiro", "https://www.freitasleiloeiro.com.br/Leiloes/Agenda", p_freitas, []),
    ("Leiloes Brasil", "https://www.leiloesbrasil.com.br/agenda", p_leiloesbrasil, []),
    ("Parque dos Leiloes", "https://www.parquedosleiloes.com.br/", p_parque, []),
]

# ---------------------------------------------------------------- coleta

async def captura(browser, url, extras):
    ctx = await browser.new_context(locale="pt-BR", user_agent=UA,
                                    viewport={"width": 1366, "height": 900})
    page = await ctx.new_page()
    apis, pend = [], []

    async def guarda(r):
        try:
            if "json" in r.headers.get("content-type", ""):
                apis.append({"url": r.url, "corpo": (await r.text())[:5_000_000]})
        except Exception:
            pass

    page.on("response", lambda r: pend.append(asyncio.ensure_future(guarda(r))))
    cap = {"texto": "", "html": "", "apis": apis, "erro": ""}
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        try:
            await page.wait_for_load_state("networkidle", timeout=25000)
        except Exception:
            pass
        await page.wait_for_timeout(4000)
        cap["html"] = await page.content()
        cap["texto"] = await page.inner_text("body")
        for e in extras:
            try:
                r = await page.request.get(e, timeout=30000)
                if r.ok:
                    apis.append({"url": e, "corpo": await r.text()})
            except Exception:
                pass
    except Exception as ex:
        cap["erro"] = repr(ex)[:300]
    if pend:
        await asyncio.gather(*pend, return_exceptions=True)
    await ctx.close()
    return cap


async def carrega_fenaju(browser):
    """Baixa a lista publica de leiloeiros da FENAJU e monta dominios oficiais."""
    ctx = await browser.new_context(user_agent=UA)
    dominios, total = {}, 0
    try:
        pagina, paginas = 1, 1
        while pagina <= paginas and pagina <= 200:
            r = await ctx.request.get(
                f"https://www.fenaju.org.br/api/public/leiloeiros?page={pagina}&origem=fenaju",
                timeout=30000)
            if not r.ok:
                break
            d = await r.json()
            paginas = d.get("totalPages", 1)
            for x in d.get("data", []):
                total += 1
                if sem_acento(x.get("situacao", "")) != "REGULAR":
                    continue
                cands = [x.get("dominio") or "", x.get("dominio_url") or ""]
                em = (x.get("email") or "").split("@")[-1].lower()
                if em and em not in EMAIL_GENERICO:
                    cands.append(em)
                for c in cands:
                    h = host(c)
                    if h:
                        dominios[h] = f"{x.get('nome', '').title()} ({x.get('juntaSigla', '')} {x.get('matricula', '')})"
            pagina += 1
            await asyncio.sleep(0.5)
    except Exception as ex:
        print("FENAJU falhou:", ex)
    await ctx.close()
    return dominios, total


def host(u):
    u = (u or "").strip().lower()
    if not u:
        return ""
    if "://" not in u:
        u = "http://" + u
    h = urlparse(u).hostname or ""
    return h[4:] if h.startswith("www.") else h


def verifica(link, dominios):
    h = host(link)
    if not h:
        return "alerta", "Sem link"
    if h.endswith(".gov.br"):
        return "ok", "Orgao publico (.gov.br)"
    for d, quem in dominios.items():
        if h == d or h.endswith("." + d):
            return "ok", "FENAJU: " + quem
    for d, quem in LISTA_CONFIAVEL.items():
        if h == d or h.endswith("." + d):
            return "ok", quem
    if h.endswith(".leilao.br") or h.endswith(".lel.br"):
        return "ok", "Dominio .leilao.br/.lel.br (restrito a leiloeiros)"
    return "alerta", "Nao verificado: confira na FENAJU antes de pagar"

# ---------------------------------------------------------------- pagina

def gera_pagina(eventos, status, n_fenaju):
    def linha(e):
        cls = "mg" if e["uf"] == "MG" else ""
        selo = "&#10004;" if e["ver"] == "ok" else "&#9888;"
        d = datetime.date.fromisoformat(e["data"])
        dia = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"][d.weekday()]
        return (f'<tr class="{cls}" data-uf="{e["uf"]}"><td>{d.strftime("%d/%m")} {dia}<br><small>{e["hora"]}</small></td>'
                f'<td><b>{e["uf"] or "?"}</b></td><td>{html.escape(e["cidade"])}</td>'
                f'<td>{html.escape(e["nome"])}<br><small>{html.escape(e["obs"])}</small></td>'
                f'<td><a href="{html.escape(e["link"])}" target="_blank" rel="noopener">{html.escape(host(e["link"]))}</a>'
                f'<br><small class="{e["ver"]}">{selo} {html.escape(e["ver_txt"])}</small></td></tr>')
    ufs = sorted({e["uf"] for e in eventos if e["uf"]})
    opcoes = "".join(f'<option value="{u}">{u}</option>' for u in ufs)
    fontes = "".join(f'<li>{html.escape(n)}: {"OK" if not s["erro"] else "FALHOU"} ({s["qtd"]} leiloes){" - " + html.escape(s["erro"][:80]) if s["erro"] else ""}</li>'
                     for n, s in status.items())
    mg = [e for e in eventos if e["uf"] == "MG"]
    resto = [e for e in eventos if e["uf"] != "MG"]
    agora = datetime.datetime.utcnow() - datetime.timedelta(hours=3)
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Radar de Leiloes</title>
<style>
body{{font-family:system-ui,Arial,sans-serif;margin:0;padding:12px;background:#f6f7f9;color:#1d2330}}
h1{{font-size:20px;margin:4px 0}} h2{{font-size:16px;margin:18px 0 6px}}
table{{border-collapse:collapse;width:100%;background:#fff;font-size:14px}}
td,th{{border-bottom:1px solid #e3e6eb;padding:6px;text-align:left;vertical-align:top}}
th{{background:#1d2330;color:#fff;position:sticky;top:0}} tr.mg td{{background:#fff7d6}}
small{{color:#5b6475}} .ok{{color:#11773a}} .alerta{{color:#b54708;font-weight:600}}
.wrap{{overflow-x:auto}} select{{font-size:15px;padding:4px}}
</style></head><body>
<h1>Radar de Leiloes de Veiculos</h1>
<div><small>Atualizado em {agora.strftime("%d/%m/%Y %H:%M")} (Brasilia) &middot; {HOJE.strftime("%d/%m")} a {LIMITE.strftime("%d/%m")} &middot;
{len(eventos)} leiloes &middot; base FENAJU: {n_fenaju} leiloeiros</small></div>
<p>Filtrar UF: <select id="f"><option value="">Todas</option>{opcoes}</select></p>
<h2>Minas Gerais ({len(mg)})</h2><div class="wrap"><table><tr><th>Data</th><th>UF</th><th>Local</th><th>Leilao</th><th>Site oficial</th></tr>
{"".join(linha(e) for e in mg) or '<tr><td colspan=5>Nenhum</td></tr>'}</table></div>
<h2>Demais estados ({len(resto)})</h2><div class="wrap"><table id="t"><tr><th>Data</th><th>UF</th><th>Local</th><th>Leilao</th><th>Site oficial</th></tr>
{"".join(linha(e) for e in resto)}</table></div>
<h2>Fontes consultadas</h2><ul>{fontes}</ul>
<p><small>&#10004; = site conferido (FENAJU, orgao publico ou organizadora conhecida). &#9888; = nao conferido: valide na FENAJU antes de qualquer pagamento. Nunca pague via Pix para pessoa fisica.</small></p>
<script>
document.getElementById('f').onchange=function(e){{var v=e.target.value;
document.querySelectorAll('tr[data-uf]').forEach(function(r){{r.style.display=(!v||r.dataset.uf===v)?'':'none'}})}};
</script></body></html>"""


async def main():
    from playwright.async_api import async_playwright
    eventos, status = [], {}
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        dominios, n_fenaju = await carrega_fenaju(browser)
        print("FENAJU:", n_fenaju, "leiloeiros,", len(dominios), "dominios")
        for nome, url, parser, extras in FONTES:
            cap = await captura(browser, url, extras)
            try:
                ev = parser(cap)
            except Exception as ex:
                ev, cap["erro"] = [], (cap["erro"] + " parser: " + repr(ex))[:300]
            ev = [e for e in ev if e["data"] and HOJE.isoformat() <= e["data"] <= LIMITE.isoformat()]
            if not ev and not cap["erro"]:
                cap["erro"] = "nenhum leilao lido (verificar se o site mudou)" if not cap["texto"] else ""
            status[nome] = {"qtd": len(ev), "erro": cap["erro"]}
            print(nome, len(ev), cap["erro"])
            eventos += ev
        await browser.close()
    vistos, unicos = set(), []
    for e in eventos:
        k = (e["data"], e["hora"], sem_acento(e["nome"])[:60], e["cidade"])
        if k in vistos:
            continue
        vistos.add(k)
        e["ver"], e["ver_txt"] = verifica(e["link"], dominios)
        unicos.append(e)
    unicos.sort(key=lambda e: (e["data"], e["hora"]))
    out = pathlib.Path("site")
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(gera_pagina(unicos, status, n_fenaju), encoding="utf-8")
    (out / "leiloes.json").write_text(json.dumps(unicos, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Total:", len(unicos))


if __name__ == "__main__":
    asyncio.run(main())
