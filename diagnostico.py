import asyncio, json, re, pathlib, gzip
from playwright.async_api import async_playwright

FONTES = [
    # Passo 23: paginas de agenda dos proximos lotes e investigacao da plataforma Superbid
    "https://www.pestanaleiloes.com.br/agenda-de-leiloes",
    "https://www.vincoleiloes.com.br/",
    "https://www.vincoleiloes.com.br/leilao.php?idLeilao=483",
    "https://www.norteleiloes.com.br/leiloes",
    "https://wrleiloes.com.br/agenda-de-leiloes",
    "https://www.leiloeiropublico.com.br/Agenda.aspx",
    "https://tulioleiloes.com.br/agenda",
    "https://www.savoyleiloes.com.br/agenda",
    "https://www.sumareleiloes.com.br/leiloes",
    "https://www.kronleiloes.com.br/",
    "https://www.kronleiloes.com.br/?searchType=opened&preOrderBy=orderByFirstOpenedOffers&pageNumber=1&pageSize=30&orderBy=endDate:asc",
    "https://www.mafraleiloes.com.br/",
    "https://www.monzonleiloes.com.br/",
    "https://www.superbid.net/",
]

# Verificacao de dominios ja feita no Passo 20 (lista vazia = nao repetir)
VERIFICAR = []

OUT = pathlib.Path("snapshots")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

def grava_gz(caminho, texto):
    # Compactado: o GitHub nao le chaves de terceiros dentro do .gz
    with gzip.open(str(caminho) + ".gz", "wt", encoding="utf-8") as f:
        f.write(texto)

def slug(u):
    s = re.sub(r"[^a-z0-9]+", "-", u.lower().split("://", 1)[-1]).strip("-")
    return s[:90]

async def captura(browser, url, sem):
    async with sem:
        d = OUT / slug(url)
        d.mkdir(parents=True, exist_ok=True)
        ctx = await browser.new_context(locale="pt-BR", user_agent=UA,
                                        viewport={"width": 1366, "height": 900},
                                        ignore_https_errors=True)
        page = await ctx.new_page()
        apis = []

        async def on_resp(r):
            try:
                ct = r.headers.get("content-type", "")
                if ("json" in ct or "xml" in ct) and len(apis) < 60:
                    corpo = await r.text()
                    apis.append({"url": r.url, "status": r.status,
                                 "metodo": r.request.method,
                                 "post": (r.request.post_data or "")[:2000],
                                 "amostra": corpo[:2_000_000]})
            except Exception:
                pass

        rede = []

        def on_any(r):
            if len(rede) < 400:
                rede.append({"url": r.url[:500], "status": r.status, "metodo": r.request.method,
                             "tipo": r.headers.get("content-type", "")[:60]})

        page.on("response", on_resp)
        page.on("response", on_any)
        info = {"url": url}
        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            info["status"] = resp.status if resp else None
            try:
                await page.wait_for_load_state("networkidle", timeout=20000)
            except Exception:
                pass
            await page.wait_for_timeout(4000)
            for _ in range(5):  # rola a pagina para carregar listas preguicosas
                await page.mouse.wheel(0, 4000)
                await page.wait_for_timeout(1500)
            info["url_final"] = page.url
            info["titulo"] = await page.title()
            html = await page.content()
            grava_gz(d / "pagina.html", html[:5_000_000])
            try:
                texto = await page.inner_text("body")
            except Exception:
                texto = ""
            grava_gz(d / "texto.txt", texto[:1_000_000])
            await page.screenshot(path=str(d / "tela.png"))
        except Exception as e:
            info["erro"] = repr(e)[:500]
        await page.wait_for_timeout(500)
        info["apis_capturadas"] = len(apis)
        grava_gz(d / "apis.json", json.dumps(apis, ensure_ascii=False, indent=1))
        grava_gz(d / "rede.json", json.dumps(rede, ensure_ascii=False, indent=1))
        (d / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
        await ctx.close()
        print(info)
        return info

async def base_fenaju(ctx, origem):
    """Baixa a base publica de leiloeiros da FENAJU (todas as paginas)."""
    regs, pagina, paginas = [], 1, 1
    while pagina <= paginas and pagina <= 300:
        url = f"https://www.fenaju.org.br/api/public/leiloeiros?page={pagina}" + (f"&origem={origem}" if origem else "")
        try:
            r = await ctx.request.get(url, timeout=30000)
            if not r.ok:
                print("FENAJU", origem, pagina, r.status)
                break
            d = await r.json()
        except Exception as ex:
            print("FENAJU erro", origem, pagina, ex)
            break
        paginas = d.get("totalPages", 1)
        regs.extend(d.get("data", []))
        pagina += 1
        await asyncio.sleep(0.4)
    return regs

async def verifica_dominios(browser):
    ctx = await browser.new_context(user_agent=UA)
    saida = {"fenaju": {}, "rdap": {}}
    for origem in ("fenaju", ""):
        regs = await base_fenaju(ctx, origem)
        saida["fenaju"][origem or "sem_origem"] = len(regs)
        grava_gz(OUT / f"fenaju_base_{origem or 'sem_origem'}.json", json.dumps(regs, ensure_ascii=False))
    for dom in VERIFICAR:
        url = (f"https://rdap.registro.br/domain/{dom}" if dom.endswith(".br")
               else f"https://rdap.verisign.com/com/v1/domain/{dom}")
        try:
            r = await ctx.request.get(url, timeout=30000)
            saida["rdap"][dom] = {"status": r.status, "corpo": (await r.text())[:20000]}
        except Exception as ex:
            saida["rdap"][dom] = {"erro": repr(ex)[:300]}
        await asyncio.sleep(0.5)
    await ctx.close()
    (OUT / "verificacao.json").write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Verificacao:", saida["fenaju"])

async def main():
    OUT.mkdir(exist_ok=True)
    # Apaga capturas antigas sem compressao, para nao misturar com as novas
    for f in OUT.glob("*/*"):
        if f.name in ("pagina.html", "texto.txt", "apis.json"):
            f.unlink()
    sem = asyncio.Semaphore(4)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            if VERIFICAR:
                await verifica_dominios(browser)
        except Exception as ex:
            print("Verificacao falhou:", ex)
        resultados = await asyncio.gather(*(captura(browser, u, sem) for u in FONTES))
        await browser.close()
    (OUT / "resumo.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=1),
                                     encoding="utf-8")

asyncio.run(main())
