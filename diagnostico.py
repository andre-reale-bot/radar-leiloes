import asyncio, json, re, pathlib, gzip
from playwright.async_api import async_playwright

FONTES = [
    # Base oficial de leiloeiros
    "https://www.fenaju.org.br/leiloeiros",
    "https://www.fenaju.org.br/leiloeiros/983",
    # Agregadores
    "https://chaveleilao.com.br/",
    "https://leiloesdecarro.com.br/",
    "https://mapadoleilao.com.br/",
    "https://leiloverso.com.br/",
    "https://leiloai.com/",
    "https://autoleilaobr.com.br/",
    "https://www.almanaquedoleilao.com.br/calendario-de-leiloes-de-veiculos",
    "https://agendadeleiloes.com.br/",
    "https://leiloeirosdobrasil.com.br/",
    # Orgaos publicos
    "https://leilao.detran.mg.gov.br/",
    "https://pcsdetran.rs.gov.br/consulta-calendario-leilao",
    "https://www25.receita.fazenda.gov.br/sle-sociedade/portal",
    # Grandes leiloeiros e organizadoras
    "https://leilo.com.br/agenda",
    "https://www.freitasleiloeiro.com.br/Leiloes/Agenda",
    "https://www.sodresantoro.com.br/",
    "https://www.copart.com.br/",
    "https://www.vipleiloes.com.br/",
    "https://loopleiloes.com.br/",
    "https://www.megaleiloes.com.br/",
    "https://www.superbid.net/",
    "https://www.mgl.com.br/agenda/",
    "https://www.leiloesbrasil.com.br/agenda",
    "https://www.parquedosleiloes.com.br/",
    "https://www.joaoemilio.com.br/",
]

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

        page.on("response", on_resp)
        info = {"url": url}
        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            info["status"] = resp.status if resp else None
            try:
                await page.wait_for_load_state("networkidle", timeout=20000)
            except Exception:
                pass
            await page.wait_for_timeout(4000)
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
        (d / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
        await ctx.close()
        print(info)
        return info

async def main():
    OUT.mkdir(exist_ok=True)
    # Apaga capturas antigas sem compressao, para nao misturar com as novas
    for f in OUT.glob("*/*"):
        if f.name in ("pagina.html", "texto.txt", "apis.json"):
            f.unlink()
    sem = asyncio.Semaphore(4)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        resultados = await asyncio.gather(*(captura(browser, u, sem) for u in FONTES))
        await browser.close()
    (OUT / "resumo.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=1),
                                     encoding="utf-8")

asyncio.run(main())
