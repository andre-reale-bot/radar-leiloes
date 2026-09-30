"""Radar de Leiloes de Veiculos - coleta diaria e gera pagina com os proximos 15 dias."""
import asyncio, json, re, pathlib, datetime, html, unicodedata, os, csv, io, time, urllib.request
from urllib.parse import urlparse

# Data de Brasilia (UTC-3). O servidor do GitHub usa UTC: sem isto, apos 21:00 a janela pulava um dia.
HOJE = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=3)).date()
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
    t = re.sub(r"\bMOTOR(ES)?\b", " ", sem_acento(texto))  # "motores" nao e moto
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
        # Horario: 'saleTime' (ex.: "120000") ja vem em Brasilia e bate com o calendario do site;
        # 'startTime' vem em UTC (15:00 = 12:00 de Brasilia). Fallback: startTime - 3 h.
        st = str(s.get("saleTime") or "")
        if re.fullmatch(r"\d{6}", st):
            hora = f"{st[:2]}:{st[2:4]}"
        else:
            m = re.fullmatch(r"(\d{1,2}):(\d{2})", s.get("startTime", "") or "")
            hora = f"{(int(m.group(1)) - 3) % 24:02d}:{m.group(2)}" if m else ""
        out.append(evento(dt, nome, "Copart", "https://www.copart.com.br/", s.get("saleName", "").split(" - ")[0],
                          acha_uf(s.get("saleName", "")), hora,
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


# ---------------------------------------------------------------- leiloeiros de MG (Passo 21)

MESES = {"JANEIRO": 1, "FEVEREIRO": 2, "MARCO": 3, "ABRIL": 4, "MAIO": 5, "JUNHO": 6, "JULHO": 7,
         "AGOSTO": 8, "SETEMBRO": 9, "OUTUBRO": 10, "NOVEMBRO": 11, "DEZEMBRO": 12}
PATIOS_PALACIO = {"JUATUBA": "MG", "CAJAMAR": "SP", "SALVADOR": "BA", "EXTERNO": ""}


def p_palacio(cap):
    """Palacio dos Leiloes (Juatuba/MG): secoes '30 de Setembro' + titulo + lotes por patio."""
    base = "https://www.palaciodosleiloes.com.br/site/index.php"
    # (qtd de lotes, id do leilao) na ordem em que aparecem no HTML
    ids = []
    for m in re.finditer(r"oferece\s*(?:<[^>]+>\s*)*(\d+)\s*(?:<[^>]+>\s*)*lotes", cap["html"]):
        m2 = re.search(r"leilao_pesquisa=(\d+)", cap["html"][m.end():m.end() + 3000])
        if m2:
            ids.append([int(m.group(1)), m2.group(1)])
    linhas = [l.strip() for l in cap["texto"].splitlines() if l.strip()]
    out = []
    for i, l in enumerate(linhas):
        m = re.fullmatch(r"(\d{1,2}) de ([A-Za-zÀ-ú]+)", l)
        if not m or i + 3 >= len(linhas) or sem_acento(m.group(2)) not in MESES:
            continue
        mes = MESES[sem_acento(m.group(2))]
        try:
            dt = datetime.date(HOJE.year, mes, int(m.group(1)))
        except ValueError:
            continue
        if dt < HOJE - datetime.timedelta(days=60):
            dt = dt.replace(year=HOJE.year + 1)
        titulo, resumo = linhas[i + 2], linhas[i + 3]
        pares = re.findall(r"([^\d]+?)\s+(\d+)", resumo)
        if not eh_veiculo(titulo + " " + resumo):
            continue
        qtd = sum(int(n) for _, n in pares) // 2
        patios = [(sem_acento(nm).strip(), int(n)) for nm, n in pares if sem_acento(nm).strip() in PATIOS_PALACIO]
        link = base
        for par in ids:
            if par[0] == qtd:
                link = "https://www.palaciodosleiloes.com.br/site/?leilao_pesquisa=" + par[1]
                ids.remove(par)
                break
        cidade, uf = "", ""
        reais = [x for x in patios if x[0] != "EXTERNO"]
        if reais:
            principal = max(reais, key=lambda x: x[1])[0]
            cidade, uf = principal.title(), PATIOS_PALACIO[principal]
        obs = "Lotes por patio: " + ", ".join(f"{nm.title()} {n}" for nm, n in patios) if patios else ""
        out.append(evento(dt, f"Palacio dos Leiloes - {titulo} ({qtd} lotes)", "Palacio dos Leiloes",
                          link, cidade, uf, "", obs))
    return out


def p_suporteleiloes(cap, fonte, dominio):
    """Sites da plataforma Suporte Leiloes (Saraiva, Kleiber): blocos 'COD. 576 / 60/2026'."""
    links = {m.group(1): m.group(0) for m in re.finditer(r"/eventos/leilao/(\d+)/[^\"'\s]*", cap["html"])}
    linhas = [l.strip() for l in cap["texto"].splitlines() if l.strip()]
    idx = [i for i, l in enumerate(linhas) if l.startswith("COD.")]
    vistos = set()
    status = {"EM BREVE", "ABERTO PARA LANCES", "ENCERRADO", "FINALIZADO", "EM LOTEAMENTO", "AO VIVO"}
    out = []
    for k, i in enumerate(idx):
        bloco = linhas[i + 1: idx[k + 1] if k + 1 < len(idx) else i + 40]
        cod = re.match(r"COD\.\s*(\d+)", linhas[i])
        titulo = next((b for b in bloco if sem_acento(b) not in status), "")
        if not titulo or not eh_veiculo(titulo):
            continue
        n_lotes = re.search(r"(\d+)\s+lotes?", linhas[i])
        link = dominio + links[cod.group(1)] if cod and cod.group(1) in links else dominio
        rotulo = "Leilao"
        for j, b in enumerate(bloco):
            if re.fullmatch(r"\dº Leil(ão|ao)|Leil(ão|ao)", b):
                rotulo = b
            if b == "Data do encerramento" and j + 1 < len(bloco):
                dt = data_br(bloco[j + 1])
                hora = bloco[j + 3] if j + 3 < len(bloco) and bloco[j + 2].startswith("A partir") else ""
                chave = (cod.group(1) if cod else titulo, str(dt), hora)
                if dt and chave not in vistos:
                    vistos.add(chave)
                    out.append(evento(dt, f"{fonte} - {titulo} ({rotulo})", fonte, link,
                                      "Online" if "ONLINE" in sem_acento(" ".join(bloco)) else "",
                                      acha_uf(titulo), hora_de(hora),
                                      f"{n_lotes.group(1)} lotes" if n_lotes else ""))
    return out


def p_saraiva(cap):
    return p_suporteleiloes(cap, "Saraiva Leiloes", "https://saraivaleiloes.com.br")


# Marcas e modelos comuns: titulos como "16 MMB L200 E TRITON, 03 STRADA" nao citam "veiculo"
MARCAS = re.compile(r"\b(FIAT|VW|VOLKSWAGEN|FORD|CHEVROLET|GM|TOYOTA|HONDA|HYUNDAI|RENAULT|NISSAN|MITSUBISHI|MMC|"
                    r"JEEP|PEUGEOT|CITROEN|STRADA|DUSTER|L200|TRITON|HILUX|S10|GOL|UNO|PALIO|SAVEIRO|AMAROK|RANGER)\b")


def p_kleiber(cap):
    """Kleiber Leiloes (Cuiaba/MT): blocos '164/2026' + tipo + comitente + titulo + datas 'dd/mm/aaaa - 09H00'."""
    linhas = [l.strip() for l in cap["texto"].splitlines() if l.strip()]
    idx = [i for i, l in enumerate(linhas) if re.fullmatch(r"\d{1,4}/20\d\d", l)]
    out = []
    for k, i in enumerate(idx):
        bloco = linhas[i + 1: idx[k + 1] if k + 1 < len(idx) else i + 30]
        if len(bloco) < 3:
            continue
        comitente, titulo = bloco[1], bloco[2]
        if not (eh_veiculo(titulo) or MARCAS.search(sem_acento(titulo))):
            continue
        junto = sem_acento(" ".join(bloco))
        modo = next((m for m in ("ONLINE", "SIMULTANEO", "PRESENCIAL") if m in junto), "")
        lotes = next((bloco[j - 1] for j, b in enumerate(bloco) if b == "LOTE(S)" and j > 0), "")
        uf = acha_uf(comitente) or acha_uf(titulo) or "MT"
        rotulo = ""
        for b in bloco:
            if "PRACA" in sem_acento(b):
                rotulo = b.title()
            m = re.fullmatch(r"(\d{2}/\d{2}/\d{4})\s*-\s*(\d{1,2})H(\d{2})", b.upper())
            if m:
                nome = f"Kleiber Leiloes - {titulo.title()}" + (f" ({rotulo})" if rotulo else "")
                out.append(evento(data_br(m.group(1)), nome, "Kleiber Leiloes", "https://www.kleiberleiloes.com.br/",
                                  "Online" if modo == "ONLINE" else "", uf, f"{int(m.group(2)):02d}:{m.group(3)}",
                                  f"{lotes} lotes; comitente: {comitente.title()}; {modo.lower()}"))
    return out


def slug_texto(s):
    return re.sub(r"[^a-z0-9]+", "-", sem_acento(s).lower()).strip("-")


def p_eleiloes(cap):
    """E-Leiloes (SP): lista 'Ver todos os leiloes' (tipo, status, titulo, lotes, 'Encerramento em 6 de Outubro')."""
    base = "https://www.e-leiloes.com.br"
    links = {}
    for m in re.finditer(r'href="(/eventos/leilao/\d+/([^"]+))"', cap["html"]):
        links[slug_texto(html.unescape(m.group(2)))] = base + m.group(1)
    linhas = [l.strip() for l in cap["texto"].splitlines() if l.strip()]
    # horarios dos "Destaques da semana": titulo ... "06/10/2026 · 10h00"
    horas = {}
    for i, l in enumerate(linhas):
        m = re.fullmatch(r"(\d{2}/\d{2}/\d{4})\s*·\s*(\d{1,2})h(\d{2})", l)
        if m:
            for j in range(i - 1, max(i - 5, 0), -1):
                if not re.search(r"LOTES|LEILAO", sem_acento(linhas[j])):
                    horas[slug_texto(linhas[j])] = f"{int(m.group(2)):02d}:{m.group(3)}"
                    break
    out = []
    for i, l in enumerate(linhas):
        m = re.fullmatch(r"Encerramento em (\d{1,2}) de ([A-Za-zÀ-ú]+)", l)
        if not m or i < 4 or sem_acento(m.group(2)) not in MESES:
            continue
        status, titulo, lotes = linhas[i - 3], linhas[i - 2], linhas[i - 1]
        if "ABERTO" not in sem_acento(status):
            continue
        if not (eh_veiculo(titulo) or "DETRAN" in sem_acento(titulo)):
            continue
        try:
            dt = datetime.date(HOJE.year, MESES[sem_acento(m.group(2))], int(m.group(1)))
        except ValueError:
            continue
        if dt < HOJE - datetime.timedelta(days=60):
            dt = dt.replace(year=HOJE.year + 1)
        sl = slug_texto(titulo)
        link = next((u for k, u in links.items() if k == sl or k.startswith(sl) or sl.startswith(k)), base)
        n = re.match(r"(\d+)", lotes)
        out.append(evento(dt, f"E-Leiloes - {titulo}", "E-Leiloes", link, "Online", acha_uf(titulo),
                          horas.get(sl, ""), f"{n.group(1)} lotes; data = encerramento" if n else "data = encerramento"))
    return out


def p_pestana(cap):
    """Pestana Leiloes (RS/PR): agenda paginada; blocos ': 433 lotes' / modo / titulo / datas."""
    linhas = [l.strip() for l in cap["texto"].splitlines() if l.strip()]
    out, vistos = [], set()
    for i, l in enumerate(linhas):
        n = re.fullmatch(r":\s*(\d+)\s+lotes?", l)
        if not n or i + 3 >= len(linhas):
            continue
        modo, titulo, datas = linhas[i + 1], linhas[i + 2], linhas[i + 3]
        if not eh_veiculo(titulo):
            continue
        pares = re.findall(r"(\d{2}/\d{2}/\d{4})\s+\w{3}\s*-\s*(\d{2}:\d{2})", datas)
        for k, (d, h) in enumerate(pares):
            rot = f" ({k + 1}o leilao)" if len(pares) > 1 else ""
            chave = (titulo, d, h)
            if chave in vistos:
                continue
            vistos.add(chave)
            out.append(evento(data_br(d), f"Pestana Leiloes - {titulo}{rot}", "Pestana Leiloes",
                              "https://www.pestanaleiloes.com.br/agenda-de-leiloes",
                              "Online" if "ONLINE" in sem_acento(modo) else "", "", h,
                              f"{n.group(1)} lotes; {modo.lower()}"))
    return out


def p_wr(cap):
    """WR Leiloes (AC/RR/AM): agenda com 'dd/mm/aaaa as hh:mm' seguido do titulo."""
    links = {slug_texto(m.group(2)): m.group(0)
             for m in re.finditer(r"https://www\.wrleiloes\.com\.br/leilao/(\d+)/([a-z0-9-]+)", cap["html"])}
    linhas = [l.strip() for l in cap["texto"].splitlines() if l.strip()]
    out = []
    for i, l in enumerate(linhas):
        m = re.fullmatch(r"(\d{2}/\d{2}/\d{4})\s+às\s+(\d{2}:\d{2})", l)
        if not m or i + 2 >= len(linhas):
            continue
        titulo, modo = linhas[i + 1], linhas[i + 2]
        if not (eh_veiculo(titulo) or "DETRAN" in sem_acento(titulo)):
            continue
        sl = slug_texto(titulo)
        link = links.get(sl) or next((u for k, u in links.items() if k.startswith(sl[:50])), "https://wrleiloes.com.br/agenda-de-leiloes")
        out.append(evento(data_br(m.group(1)), f"WR Leiloes - {titulo}", "WR Leiloes", link,
                          "Online" if "ONLINE" in sem_acento(modo) else "",
                          acha_uf(titulo) or next(iter(re.findall(r"DETRAN\s*-\s*([A-Z]{2})\b", sem_acento(titulo))), ""),
                          m.group(2), modo))
    return out


MESES3 = {"JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6, "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10,
          "NOV": 11, "DEZ": 12}


def p_norte(cap):
    """Norte Leiloes (PA/AM/MA): API sistema.norteleiloes.com.br/index/leiloes2 (paginada)."""
    out, vistos = [], set()
    for a in cap["apis"]:
        if "index/leiloes2" not in a["url"]:
            continue
        try:
            lista = json.loads(a["corpo"]).get("dados", [])
        except Exception:
            continue
        for x in lista:
            if x.get("LEI_ID") in vistos:
                continue
            vistos.add(x.get("LEI_ID"))
            nome, local = x.get("LEI_NOME") or "", x.get("LRL_NOME") or ""
            if (x.get("LEI_SITE_SITUACAO") or "") in ("CANCELADO", "SUSPENSO", "REALIZADO", "ENCERRADO"):
                continue
            if not eh_veiculo(nome):
                continue
            try:
                dt = datetime.date.fromisoformat(x.get("LED_DIA") or "")
            except ValueError:
                continue
            h = re.search(r"(\d{1,2})h(\d{2})", x.get("LED_DIA_F") or "")
            out.append(evento(dt, f"Norte Leiloes - {nome.title()}", "Norte Leiloes",
                              x.get("urlLeilao") or "https://www.norteleiloes.com.br/leiloes",
                              "Online" if "ONLINE" in sem_acento(local) else "", acha_uf(local) or acha_uf(nome),
                              f"{int(h.group(1)):02d}:{h.group(2)}" if h else "",
                              f"{x.get('LEI_QTD_LOTES') or '?'} lotes; {local.title()}"))
    return out


def p_leiloeiropublico(cap):
    """Leiloeiro Publico (SC/PR): API api-lances.leiloeiropublico.com.br/leilao/agenda/ativos/todos."""
    d = _json(cap, "leilao/agenda/ativos")
    out = []
    for x in d or []:
        titulo = html.unescape(re.sub(r"<[^>]+>", "", x.get("titulo") or "")).strip()
        if x.get("status") == "Encerrado" or x.get("vendaDireta"):
            continue
        if not eh_veiculo(titulo + " " + (x.get("resumo") or "")):
            continue
        m = re.search(r":\s*(.+?)\s*\(([A-Z]{2})\)", titulo)
        cidade, uf = (m.group(1), m.group(2)) if m else ("", acha_uf(titulo))
        link = f"https://www.leiloeiropublico.com.br/ListagemLote.aspx?Leilao={x.get('id')}"
        datas = [x.get("dataHora1") or ""]
        if (x.get("dataHora2") or "")[:10] != datas[0][:10]:
            datas.append(x.get("dataHora2") or "")
        for k, dh in enumerate(datas):
            try:
                dt = datetime.date.fromisoformat(dh[:10])
            except ValueError:
                continue
            rot = f" ({k + 1}o leilao)" if len(datas) > 1 else ""
            out.append(evento(dt, f"Leiloeiro Publico - {titulo}{rot}", "Leiloeiro Publico", link, cidade, uf,
                              dh[11:16], (x.get("resumo") or "").strip()))
    return out


def p_leilotech(cap, fonte, base):
    """Plataforma Leilotech (ex.: Tulio Leiloes): GraphQL 'Agenda' capturado ao abrir /agenda."""
    out = []
    for a in cap["apis"]:
        if "graphql" not in a["url"]:
            continue
        try:
            itens = json.loads(a["corpo"])["data"]["agenda"]["items"]
        except Exception:
            continue
        for it in itens:
            le = it.get("leilao") or {}
            if it.get("suspensa") or it.get("retirada"):
                continue
            titulo = le.get("title") or ""
            if not eh_veiculo(titulo + " " + (le.get("description") or "")):
                continue
            try:
                dt = datetime.date.fromisoformat((it.get("data") or "")[:10])
            except ValueError:
                continue
            loc = le.get("location") or {}
            out.append(evento(dt, f"{fonte} - {titulo.title()}", fonte, base + "/agenda",
                              loc.get("city") or "", loc.get("uf") or "", (it.get("data") or "")[11:16],
                              f"{le.get('lotesCount', '?')} lotes; comitente: {(le.get('comitente') or {}).get('nome', '')}"))
    return out


def p_tulio(cap):
    return p_leilotech(cap, "Tulio Leiloes", "https://tulioleiloes.com.br")


def p_savoy(cap):
    """Savoy Leiloes (SP): API api.savoyleiloes.com.br/rest/v1/auctions (fases com data de encerramento em UTC)."""
    out = []
    for a in cap["apis"]:
        if "rest/v1/auctions" not in a["url"]:
            continue
        try:
            lista = json.loads(a["corpo"])
        except Exception:
            continue
        for x in lista:
            titulo, sub = (x.get("title") or "").strip(), (x.get("subtitle") or "").strip(' "')
            if not eh_veiculo(titulo + " " + sub):
                continue
            m = re.search(r"de ([A-Za-zÀ-ú ]+?)\s*-\s*([A-Z]{2})\b", titulo)
            cidade, uf = (m.group(1).strip(), m.group(2)) if m else ("", acha_uf(titulo))
            for f in x.get("auction_phases") or []:
                if f.get("completed"):
                    continue
                try:
                    utc = datetime.datetime.fromisoformat(f["end_date"])
                except (KeyError, ValueError):
                    continue
                br = utc - datetime.timedelta(hours=3)
                out.append(evento(br.date(), f"Savoy Leiloes - {titulo}", "Savoy Leiloes",
                                  "https://www.savoyleiloes.com.br/agenda", cidade, uf, br.strftime("%H:%M"),
                                  f"{x.get('lots_count', '?')} lotes; {sub}; data = encerramento"))
    return out


def p_vinco(cap):
    """Vinco Leiloes (SP): cards da capa (exige rolar a pagina). 'ID: 483' + titulo + datas 'Qua, 30/Set/2026, 10h00'."""
    linhas = [l.strip() for l in cap["texto"].splitlines() if l.strip()]
    out = []
    i = 0
    while i < len(linhas) - 1:
        m = re.fullmatch(r"(?:ID:?\s*)?(\d{2,4})", linhas[i])
        if not m or len(linhas[i + 1]) < 15:
            i += 1
            continue
        lid, titulo = m.group(1), linhas[i + 1]
        j, bloco = i + 2, []
        while j < len(linhas) and not re.fullmatch(r"(?:ID:?\s*)?\d{2,4}", linhas[j]) and len(bloco) < 8:
            bloco.append(linhas[j])
            j += 1
        i = j
        junto = sem_acento(" ".join(bloco))
        if "ENCERRADO" in junto or "SUSTADO" in junto:
            continue
        if not (eh_veiculo(titulo) or MARCAS.search(sem_acento(titulo))):
            continue
        for b in bloco:
            d = re.search(r"(\d{2})/([A-Za-z]{3})/(\d{4}),\s*(\d{1,2})h(\d{2})", b)
            if not d or sem_acento(d.group(2)) not in MESES3:
                continue
            try:
                dt = datetime.date(int(d.group(3)), MESES3[sem_acento(d.group(2))], int(d.group(1)))
            except ValueError:
                continue
            rot = f" ({b.split(':')[0]})" if "PRACA" in sem_acento(b) else ""
            cid = re.search(r"[-–]\s*([A-Za-zÀ-ú .']+?)\s*/\s*([A-Z]{2})\s*$", titulo)
            out.append(evento(dt, f"Vinco Leiloes - {titulo}{rot}", "Vinco Leiloes",
                              f"https://www.vincoleiloes.com.br/leilao.php?idLeilao={lid}",
                              cid.group(1).strip() if cid else "", cid.group(2) if cid else acha_uf(titulo),
                              f"{int(d.group(4)):02d}:{d.group(5)}", ""))
    return out


def p_cardoso(cap):
    """Cardoso Leiloes (SP): titulo seguido de '1o Leilao: dd/mm/aaaa as hh:mm'."""
    linhas = [l.strip() for l in cap["texto"].splitlines() if l.strip()]
    out, vistos = [], set()
    inicios = [i for i, l in enumerate(linhas) if re.match(r"1º Leil", l) and i > 0]
    for k, i in enumerate(inicios):
        titulo = linhas[i - 1]
        fim = inicios[k + 1] - 1 if k + 1 < len(inicios) else i + 12
        bloco = linhas[i: min(fim, i + 12)]
        detalhes = " ".join(bloco)
        if not (eh_veiculo(titulo + " " + detalhes) or MARCAS.search(sem_acento(titulo + " " + detalhes))):
            continue
        if any(p in sem_acento(titulo) for p in ("APTO", "APARTAMENTO", "RUA ", "CASA", "TERRENO", "IMOVEL")):
            continue
        for b in bloco:
            m = re.match(r"(\d)º Leil\S*:\s*(\d{2}/\d{2}/\d{4})\s+às\s+(\d{2}:\d{2})", b)
            if m and (titulo, m.group(2)) not in vistos:
                vistos.add((titulo, m.group(2)))
                out.append(evento(data_br(m.group(2)), f"Cardoso Leiloes - {titulo} ({m.group(1)}o leilao)",
                                  "Cardoso Leiloes", "https://www.cardosoleiloes.com.br/",
                                  "Online" if "ONLINE" in sem_acento(detalhes) else "", acha_uf(titulo), m.group(3), ""))
    return out


def p_freire(cap):
    """Leiloes Freire (AL/PE/SE): comitente, 'dd/mm/aaaa as hh:mm', modo, status, local, '- Cidade - UF'."""
    linhas = [l.strip() for l in cap["texto"].splitlines() if l.strip()]
    out = []
    for i, l in enumerate(linhas):
        m = re.fullmatch(r"(\d{2}/\d{2}/\d{4})\s+às\s+(\d{2}:\d{2})", l)
        if not m or i == 0:
            continue
        comitente = linhas[i - 1]
        bloco = linhas[i + 1: i + 6]
        if not eh_veiculo(comitente + " " + " ".join(bloco[:3])):
            continue
        cid = next((re.match(r"-?\s*(.+?)\s*-\s*([A-Z]{2})$", b) for b in bloco if re.match(r"-?\s*.+?\s*-\s*[A-Z]{2}$", b)), None)
        out.append(evento(data_br(m.group(1)), f"Leiloes Freire - {comitente.title()}", "Leiloes Freire",
                          "https://www.leiloesfreire.com.br/", cid.group(1) if cid else "",
                          cid.group(2) if cid else acha_uf(comitente), m.group(2), " ".join(bloco[:2])))
    return out


def p_astavero(cap, fonte, base):
    """Plataforma dos sites Top/Pizzolatti e Sampaio: API app/lotes (lotes agrupados por leilao)."""
    grupos = {}
    for a in cap["apis"]:
        if not a["url"].endswith("/app/lotes"):
            continue
        try:
            lotes = json.loads(a["corpo"]).get("lotes", [])
        except Exception:
            continue
        for x in lotes:
            g = grupos.setdefault(x.get("leilao"), {"lotes": {}, "x": x})
            g["lotes"][x.get("id")] = x
    out = []
    for lid, g in grupos.items():
        lotes = list(g["lotes"].values())
        veic = [x for x in lotes if eh_veiculo(x.get("nome") or "") or MARCAS.search(sem_acento(x.get("nome") or ""))]
        x = g["x"]
        if not veic or "TESTE" in sem_acento(x.get("vara") or ""):
            continue
        try:
            dt = datetime.date.fromisoformat((x.get("data") or "")[:10])
        except ValueError:
            continue
        loc = re.match(r"(.+?)\s*-\s*([A-Z]{2})$", x.get("local") or "")
        exemplos = ", ".join((v.get("nome") or "")[:40] for v in veic[:3])
        out.append(evento(dt, f"{fonte} - {x.get('vara') or 'Leilao'}", fonte,
                          x.get("url") or base, loc.group(1) if loc else "", loc.group(2) if loc else "",
                          (x.get("data") or "")[11:16],
                          f"{len(veic)} veiculo(s) entre os lotes vistos: {exemplos}"))
    return out


def p_top(cap):
    return p_astavero(cap, "Top Leiloes (Pizzolatti)", "https://topleiloes.com.br")


def p_sampaio(cap):
    return p_astavero(cap, "Sampaio Leiloes", "https://sampaioleiloes.com.br")


def p_gp(cap):
    """GP Leiloes (BH): API gp-api/index/inicio (agenda), com 1a e 2a praca."""
    out, vistos = [], set()
    for a in cap["apis"]:
        if "gp-api/index/inicio" not in a["url"]:
            continue
        try:
            lista = json.loads(a["corpo"]).get("value", {}).get("content", [])
        except Exception:
            continue
        for x in lista:
            cod = x.get("codigoLeilao")
            if cod in vistos:
                continue
            vistos.add(cod)
            lote = x.get("lote") or {}
            texto = " ".join(str(v) for v in (x.get("titulo"), x.get("descricao"), lote.get("resumo")) if v)
            if not eh_veiculo(texto):
                continue
            loc = lote.get("localizacao") or ""
            cidade = loc.split("/")[0].title() if loc else ("Online" if x.get("tipoDescricao") == "Online" else "")
            uf = acha_uf(loc) if loc else ""
            obs = f"{x.get('numeroDeLotes', '')} lotes; comitente: {(x.get('comitente') or '').strip(' -')}"
            pracas = [(x.get("data"), x.get("hora"), "1a praca")]
            if x.get("data2"):
                pracas.append((x.get("data2"), x.get("hora2"), "2a praca"))
            for d, h, rot in pracas:
                try:
                    dt = datetime.date.fromisoformat(d)
                except (TypeError, ValueError):
                    continue
                nome = f"GP Leiloes - {x.get('titulo', '').strip()}" + (f" ({rot})" if len(pracas) > 1 else "")
                out.append(evento(dt, nome, "GP Leiloes", f"https://www.gpleiloes.com.br/#leilao/{cod}",
                                  cidade, uf, h or "", obs))
    return out


def p_leiloes_mg(cap):
    """Portal de leiloes do Governo de MG (Seplag). Sem exemplo real com leilao aberto ainda:
    se a mensagem de 'nenhum leilao' sumir, gera um aviso para conferir no site."""
    t = sem_acento(cap["texto"])
    if not t or "NAO EXISTE NENHUM LEILAO" in t:
        return []
    return [evento(HOJE, "Governo de MG (Seplag): ha leiloes publicados, conferir no site", "Leiloes MG (Seplag)",
                   "https://www.leiloes.mg.gov.br/", "Belo Horizonte", "MG", "",
                   "Leitor ainda nao conhece o formato; revisar manualmente")]


# Consulta de todos os lotes abertos (agenda) da plataforma de Top e Sampaio
LOTES_POST = {"botao": "AGENDA DE LEILÕES", "origem": "", "comitente": "", "categoria": "", "categ": -1, "sub": "",
              "isub": -1, "uf": "", "cidade": "", "busca": "", "mes": HOJE.isoformat(), "s3url": "", "page": 0,
              "pages": 0, "limite": 300, "count": 0}

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
    ("Palacio dos Leiloes", "https://www.palaciodosleiloes.com.br/site/index.php", p_palacio, []),
    ("Saraiva Leiloes", "https://saraivaleiloes.com.br/", p_saraiva, []),
    ("GP Leiloes", "https://www.gpleiloes.com.br/", p_gp,
     [{"url": "https://www.gpleiloes.com.br/gp-api/index/inicio/1/60", "post": {"filtro": None}}]),
    ("Leiloes MG (Seplag)", "https://www.leiloes.mg.gov.br/", p_leiloes_mg, []),
    ("Kleiber Leiloes", "https://kleiberleiloes.com.br/", p_kleiber, []),
    ("E-Leiloes", "https://www.e-leiloes.com.br/", p_eleiloes, []),
    ("Pestana Leiloes", "https://www.pestanaleiloes.com.br/agenda-de-leiloes", p_pestana,
     [{"clicar": "Próximo", "vezes": 4}]),
    ("WR Leiloes", "https://wrleiloes.com.br/agenda-de-leiloes", p_wr, []),
    ("Norte Leiloes", "https://www.norteleiloes.com.br/leiloes", p_norte,
     [f"https://www.sistema.norteleiloes.com.br/index/leiloes2?pagina={n}&porPagina=12&&api=true" for n in (2, 3, 4)]),
    ("Leiloeiro Publico", "https://www.leiloeiropublico.com.br/Agenda.aspx", p_leiloeiropublico, []),
    ("Tulio Leiloes", "https://tulioleiloes.com.br/agenda", p_tulio, []),
    ("Savoy Leiloes", "https://www.savoyleiloes.com.br/agenda", p_savoy, []),
    ("Vinco Leiloes", "https://www.vincoleiloes.com.br/", p_vinco, [{"rolar": 5}]),
    ("Cardoso Leiloes", "https://www.cardosoleiloes.com.br/", p_cardoso, []),
    ("Leiloes Freire", "https://www.leiloesfreire.com.br/", p_freire, []),
    ("Top Leiloes (Pizzolatti)", "https://topleiloes.com.br/home", p_top,
     [{"url": "https://topleiloes.com.br/app/lotes", "post": dict(LOTES_POST, dom="pizzolatti")}]),
    ("Sampaio Leiloes", "https://sampaioleiloes.com.br/home", p_sampaio,
     [{"url": "https://sampaioleiloes.com.br/app/lotes", "post": dict(LOTES_POST, dom="sampaio")}]),
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
    cap = {"texto": "", "html": "", "apis": apis, "erro": "", "status": None, "url_final": ""}
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        cap["status"] = resp.status if resp else None
        try:
            await page.wait_for_load_state("networkidle", timeout=25000)
        except Exception:
            pass
        await page.wait_for_timeout(4000)
        cap["html"] = await page.content()
        cap["texto"] = await page.inner_text("body")
        cap["url_final"] = page.url
        for e in extras:
            try:
                if isinstance(e, dict) and "rolar" in e:  # rola a pagina para carregar cards preguicosos
                    for _ in range(e["rolar"]):
                        await page.mouse.wheel(0, 4000)
                        await page.wait_for_timeout(1500)
                    cap["texto"] = await page.inner_text("body")
                    cap["html"] = await page.content()
                    continue
                if isinstance(e, dict) and "clicar" in e:  # paginacao: clica em "Proximo" e junta o texto
                    for _ in range(e.get("vezes", 1)):
                        botao = page.get_by_text(e["clicar"], exact=True).first
                        if not await botao.count():
                            break
                        await botao.click(timeout=10000)
                        await page.wait_for_timeout(3500)
                        cap["texto"] += "\n" + await page.inner_text("body")
                    continue
                if isinstance(e, dict):  # consulta POST (ex.: agenda completa da GP)
                    r = await page.request.post(e["url"], data=json.dumps(e["post"]),
                                                headers={"Content-Type": "application/json"}, timeout=30000)
                    u = e["url"]
                else:
                    r = await page.request.get(e, timeout=30000)
                    u = e
                if r.ok:
                    apis.append({"url": u, "corpo": await r.text()})
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

# ---------------------------------------------------------------- distancias

MUNICIPIOS_URL = "https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/municipios.csv"
ESTADOS_URL = "https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/estados.csv"
OSRM_URL = "https://router.project-osrm.org/table/v1/driving/"
FATOR_TEMPO = 1.10  # pedido do usuario: tempo do OpenStreetMap + 10%
ORIGEM = ("BELO HORIZONTE", "MG")


def nome_cidade(s):
    """Normaliza nome de cidade para comparacao (sem acento, sem pontuacao)."""
    t = sem_acento(s).replace("'", "")
    t = re.sub(r"[^A-Z ]", " ", t)
    return " ".join(t.split())


def baixa_texto(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "radar-leiloes (github.com/andre-reale-bot)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8-sig")


def carrega_municipios():
    """Coordenadas das sedes dos municipios (base IBGE compilada no GitHub kelvins)."""
    ufs = {row["codigo_uf"]: row["uf"] for row in csv.DictReader(io.StringIO(baixa_texto(ESTADOS_URL)))}
    por_uf, por_nome = {}, {}
    for row in csv.DictReader(io.StringIO(baixa_texto(MUNICIPIOS_URL))):
        uf = ufs.get(row["codigo_uf"], "")
        n = nome_cidade(row["nome"])
        coord = (float(row["longitude"]), float(row["latitude"]))
        por_uf[(n, uf)] = coord
        por_nome.setdefault(n, []).append((uf, coord))
    return por_uf, por_nome


def acha_coord(e, por_uf, por_nome):
    n = nome_cidade(e["cidade"])
    if (n, e["uf"]) not in por_uf:
        n = re.sub(r" (%s)$" % "|".join(UFS), "", n)  # tira UF colada no fim ("BETIM MG")
        n = re.sub(r"^(LEILAO |PATIO )+", "", n)  # "PATIO FORTALEZA" -> "FORTALEZA"
    if not n:
        return None, ""
    if e["uf"] and (n, e["uf"]) in por_uf:
        return por_uf[(n, e["uf"])], e["uf"]
    if not e["uf"] and len(por_nome.get(n, [])) == 1:  # nome unico no Brasil
        uf, c = por_nome[n][0]
        return c, uf
    return None, ""


def formata_tempo(seg):
    m = int(round(seg * FATOR_TEMPO / 60))
    if m < 60:
        return f"{m} min"
    return f"{m // 60}h{m % 60:02d}"


def calcula_distancias(eventos):
    """Distancia e tempo de carro de BH ate a cidade de cada leilao (OpenStreetMap/OSRM)."""
    for e in eventos:
        e["km"], e["tempo"] = None, ""
    try:
        por_uf, por_nome = carrega_municipios()
    except Exception as ex:
        print("Municipios falhou:", ex)
        return "base de municipios indisponivel"
    origem = por_uf.get(ORIGEM)
    if not origem:
        return "origem (BH) nao encontrada na base"
    destinos = {}
    for e in eventos:
        c, _ = acha_coord(e, por_uf, por_nome)
        if c:
            destinos.setdefault(c, []).append(e)
    lista = list(destinos)
    falhas = 0
    for i in range(0, len(lista), 80):
        lote = lista[i:i + 80]
        coords = ";".join(f"{lon:.5f},{lat:.5f}" for lon, lat in [origem] + lote)
        try:
            d = json.loads(baixa_texto(OSRM_URL + coords + "?sources=0&annotations=duration,distance"))
            if d.get("code") != "Ok":
                raise ValueError(d.get("code"))
            for j, c in enumerate(lote, start=1):
                dist, dur = d["distances"][0][j], d["durations"][0][j]
                if dist is None or dur is None:
                    continue
                for e in destinos[c]:
                    e["km"], e["tempo"] = int(round(dist / 1000)), formata_tempo(dur)
        except Exception as ex:
            falhas += 1
            print("OSRM falhou:", ex)
        time.sleep(1.2)
    com = sum(1 for e in eventos if e["km"] is not None)
    print("Distancias:", com, "de", len(eventos), "leiloes")
    return f"{com} de {len(eventos)} leiloes com distancia" + (" (OSRM falhou em parte)" if falhas else "")

# ---------------------------------------------------------------- saude das fontes (contingencia)

SAUDE_URL = "https://andre-reale-bot.github.io/radar-leiloes/saude.json"  # historico publicado na propria pagina


def dominio_base(u):
    """Dominio base para comparar redirecionamentos: 3 rotulos em .com.br/.gov.br etc., 2 no resto."""
    h = host(u)
    partes = h.split(".")
    if len(partes) >= 3 and partes[-1] == "br" and len(partes[-2]) <= 3:
        return ".".join(partes[-3:])
    return ".".join(partes[-2:])


def carrega_saude():
    try:
        return json.loads(baixa_texto(SAUDE_URL, timeout=30))
    except Exception as ex:
        print("Historico de saude indisponivel (normal na 1a vez):", ex)
        return {"fontes": {}, "rdap": {}}


def avalia_saude(saude, nome, url, cap, qtd):
    """Atualiza o historico da fonte e devolve a lista de alertas dela."""
    hoje = HOJE.isoformat()
    f = saude["fontes"].setdefault(nome, {"qtds": {}, "falha_desde": None})
    alertas = []
    falhou = bool(cap["erro"] and not cap["texto"]) or (cap["status"] or 200) >= 400
    if falhou:
        f["falha_desde"] = f["falha_desde"] or hoje
        if f["falha_desde"] < hoje:
            alertas.append(f"site fora do ar ou com erro desde {f['falha_desde']} "
                           f"(status {cap['status'] or 'sem resposta'})")
    else:
        f["falha_desde"] = None
    if cap["url_final"] and dominio_base(cap["url_final"]) != dominio_base(url):
        alertas.append(f"o site redirecionou para outro dominio: {host(cap['url_final'])}")
    anteriores = [v for d, v in sorted(f["qtds"].items()) if d < hoje][-7:]
    if not falhou and qtd == 0 and len(anteriores) >= 2 and sorted(anteriores)[len(anteriores) // 2] >= 1:
        alertas.append("nenhum leilao lido hoje, mas a fonte costuma ter; o site pode ter mudado de layout")
    if not falhou:
        f["qtds"][hoje] = qtd
        f["qtds"] = dict(sorted(f["qtds"].items())[-14:])
    return alertas


def verifica_dominios_semanal(saude):
    """Uma vez por semana consulta o Registro.br (RDAP): dominio vencido ou titular diferente."""
    alertas, agora = {}, HOJE.isoformat()
    ultimo = saude.get("rdap_data", "")
    if ultimo and (HOJE - datetime.date.fromisoformat(ultimo)).days < 7:
        return saude.get("rdap_alertas", {})
    doms = sorted({dominio_base(u) for _, u, _, _ in FONTES if not host(u).endswith(".gov.br")})
    for d in doms:
        if not d.endswith(".br"):
            continue
        try:
            j = json.loads(baixa_texto(f"https://rdap.registro.br/domain/{d}", timeout=30))
        except Exception as ex:
            print("RDAP falhou", d, ex)
            continue
        titular = ""
        for e in j.get("entities", []):
            if "registrant" in e.get("roles", []):
                titular = next((a[3] for a in e.get("vcardArray", [None, []])[1] if a[0] == "fn"), "")
        venc = next((e["eventDate"][:10] for e in j.get("events", []) if e.get("eventAction") == "expiration"), "")
        antes = saude["rdap"].get(d, {})
        if venc and venc < agora:
            alertas[d] = f"dominio {d} venceu em {venc}"
        elif antes.get("titular") and titular and antes["titular"] != titular:
            alertas[d] = f"dominio {d} mudou de titular ({antes['titular']} -> {titular})"
        saude["rdap"][d] = {"titular": antes.get("titular") or titular, "vencimento": venc}
        time.sleep(0.5)
    saude["rdap_data"], saude["rdap_alertas"] = agora, alertas
    return alertas

# ---------------------------------------------------------------- pagina

def gera_pagina(eventos, status, n_fenaju, info_dist="", alertas=None):
    def dist(e):
        if e.get("km") is None:
            return "<small>Online</small>" if nome_cidade(e["cidade"]) == "ONLINE" else "<small>?</small>"
        if e["km"] == 0:
            return "Em BH"
        return f'{e["km"]} km<br><small>{e["tempo"]}</small>'

    def linha(e):
        cls = "mg" if e["uf"] == "MG" else ""
        selo = "&#10004;" if e["ver"] == "ok" else "&#9888;"
        d = datetime.date.fromisoformat(e["data"])
        dia = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"][d.weekday()]
        km = e["km"] if e.get("km") is not None else 999999  # sem distancia vai para o fim
        dt = e["data"] + " " + (e["hora"] or "00:00")
        return (f'<tr class="{cls}" data-uf="{e["uf"]}" data-km="{km}" data-dt="{dt}"><td>{d.strftime("%d/%m")} {dia}<br><small>{e["hora"]}</small></td>'
                f'<td><b>{e["uf"] or "?"}</b></td><td>{html.escape(e["cidade"])}</td>'
                f'<td>{dist(e)}</td>'
                f'<td>{html.escape(e["nome"])}<br><small>{html.escape(e["obs"])}</small></td>'
                f'<td><a href="{html.escape(e["link"])}" target="_blank" rel="noopener">{html.escape(host(e["link"]))}</a>'
                f'<br><small class="{e["ver"]}">{selo} {html.escape(e["ver_txt"])}</small></td></tr>')
    faixa = ""
    if alertas:
        itens = "".join(f"<li><b>{html.escape(n)}</b>: {html.escape(m)}</li>" for n, m in alertas)
        faixa = ('<div class="faixa"><b>ATENCAO: fontes com problema.</b> Procure o site novo destes leiloeiros '
                 f'para substituirmos no radar:<ul>{itens}</ul></div>')
    ufs = sorted({e["uf"] for e in eventos if e["uf"]})
    opcoes = "".join(f'<option value="{u}">{u}</option>' for u in ufs)
    fontes = "".join(f'<li>{html.escape(n)}: {"OK" if not s["erro"] else "FALHOU"} ({s["qtd"]} leiloes){" - " + html.escape(s["erro"][:80]) if s["erro"] else ""}</li>'
                     for n, s in status.items())
    n_mg = sum(1 for e in eventos if e["uf"] == "MG")
    # Ordem padrao: mais perto de BH primeiro; sem distancia no fim; empate por data
    por_dist = sorted(eventos, key=lambda e: (e["km"] if e.get("km") is not None else 999999,
                                              e["data"], e["hora"]))
    agora = datetime.datetime.utcnow() - datetime.timedelta(hours=3)
    tipo = {"schedule": "execucao automatica", "workflow_dispatch": "execucao manual"}.get(
        os.environ.get("GITHUB_EVENT_NAME", ""), "execucao fora do GitHub")
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Radar de Leiloes</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📡</text></svg>">
<style>
body{{font-family:system-ui,Arial,sans-serif;margin:0;padding:12px;background:#f6f7f9;color:#1d2330}}
h1{{font-size:20px;margin:4px 0}} h2{{font-size:16px;margin:18px 0 6px}}
table{{border-collapse:collapse;width:100%;background:#fff;font-size:14px}}
td,th{{border-bottom:1px solid #e3e6eb;padding:6px;text-align:left;vertical-align:top}}
th{{background:#1d2330;color:#fff;position:sticky;top:0}} tr.mg td{{background:#fff7d6}}
small{{color:#5b6475}} .ok{{color:#11773a}} .alerta{{color:#b54708;font-weight:600}}
.wrap{{overflow-x:auto}} select,button{{font-size:15px;padding:4px 8px}}
button.on{{background:#1d2330;color:#fff}}
.faixa{{background:#fde8e8;border:2px solid #c81e1e;color:#7a1010;padding:10px 12px;margin:10px 0;border-radius:6px}}
</style></head><body>
<h1>Radar de Leiloes de Veiculos</h1>
{faixa}
<div><small>Atualizado em {agora.strftime("%d/%m/%Y %H:%M")} (Brasilia, {tipo}) &middot; {HOJE.strftime("%d/%m")} a {LIMITE.strftime("%d/%m")} &middot;
{len(eventos)} leiloes &middot; base FENAJU: {n_fenaju} leiloeiros</small></div>
<p>Filtrar UF: <select id="f"><option value="">Todas</option>{opcoes}</select>
&nbsp; Ordenar: <button id="bk" class="on">Por distancia</button> <button id="bd">Por data</button></p>
<h2>Leiloes ({len(eventos)}) &middot; <span style="background:#fff7d6;padding:0 4px">Minas Gerais em amarelo ({n_mg})</span></h2>
<div class="wrap"><table><thead><tr><th>Data</th><th>UF</th><th>Local</th><th>De BH (carro)</th><th>Leilao</th><th>Site oficial</th></tr></thead>
<tbody id="t">{"".join(linha(e) for e in por_dist) or '<tr><td colspan=6>Nenhum</td></tr>'}</tbody></table></div>
<h2>Fontes consultadas</h2><ul>{fontes}</ul>
<p><small>&#10004; = site conferido (FENAJU, orgao publico ou organizadora conhecida). &#9888; = nao conferido: valide na FENAJU antes de qualquer pagamento. Nunca pague via Pix para pessoa fisica.</small></p>
<p><small>De BH (carro): distancia e tempo de carro a partir de Belo Horizonte ate a sede do municipio, calculados pelo OpenStreetMap (OSRM), com tempo acrescido de 10%. Sem transito. ? = cidade nao identificada. {html.escape(info_dist)}.</small></p>
<script>
document.getElementById('f').onchange=function(e){{var v=e.target.value;
document.querySelectorAll('tr[data-uf]').forEach(function(r){{r.style.display=(!v||r.dataset.uf===v)?'':'none'}})}};
function ordena(porKm){{var t=document.getElementById('t');
var rs=Array.prototype.slice.call(t.querySelectorAll('tr[data-uf]'));
rs.sort(function(a,b){{var ka=+a.dataset.km,kb=+b.dataset.km,da=a.dataset.dt,db=b.dataset.dt;
if(porKm){{return (ka-kb)||(da<db?-1:da>db?1:0)}}return (da<db?-1:da>db?1:0)||(ka-kb)}});
rs.forEach(function(r){{t.appendChild(r)}});
document.getElementById('bk').className=porKm?'on':'';document.getElementById('bd').className=porKm?'':'on'}}
document.getElementById('bk').onclick=function(){{ordena(true)}};
document.getElementById('bd').onclick=function(){{ordena(false)}};
</script></body></html>"""


async def main():
    from playwright.async_api import async_playwright
    eventos, status, alertas = [], {}, []
    saude = carrega_saude()
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
            try:
                alertas += [(nome, m) for m in avalia_saude(saude, nome, url, cap, len(ev))]
            except Exception as ex:
                print("Saude falhou", nome, ex)
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
    info_dist = calcula_distancias(unicos)
    try:
        for d, m in verifica_dominios_semanal(saude).items():
            alertas.append((d, m))
    except Exception as ex:
        print("RDAP semanal falhou:", ex)
    out = pathlib.Path("site")
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(gera_pagina(unicos, status, n_fenaju, info_dist, alertas), encoding="utf-8")
    (out / "saude.json").write_text(json.dumps(saude, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "leiloes.json").write_text(json.dumps(unicos, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Total:", len(unicos))


if __name__ == "__main__":
    asyncio.run(main())
