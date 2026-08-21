#(©)Codexbotz
#rymme

from aiohttp import web
from miniapp_interstitial import (
    complete,
    interstitial_done,
    interstitial_miniapp,
    rewarded_popup_done,
    verification_page,
    start_ad,
    complete_ad,
)

routes = web.RouteTableDef()


@routes.get("/", allow_head=True)
async def root_route_handler(request):
    html = """
    <!doctype html>
    <html lang='en'>
    <head>
      <meta charset='utf-8' />
      <meta name='viewport' content='width=device-width,initial-scale=1' />
      <meta name='theme-color' content='#0f172a' />
      <title>Uchiha Developer | Secure File Verification</title>
      <link rel='icon' href='/favicon.ico' />
      <style>
        :root { --bg:#f8fafc; --card:#ffffff; --text:#0f172a; --muted:#475569; --primary:#2563eb; --accent:#7c3aed; }
        * { box-sizing: border-box; }
        body { margin: 0; font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); }
        .wrap { max-width: 1040px; margin: 0 auto; padding: 28px 18px 40px; }
        header { display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom: 28px; }
        .brand { font-weight:800; font-size:1.2rem; }
        .hero { background: linear-gradient(135deg, #1d4ed8, #7c3aed); color:#fff; border-radius:20px; padding:34px 22px; box-shadow: 0 10px 24px rgba(15,23,42,.16); }
        h1 { margin:0 0 10px; font-size:clamp(1.7rem,4vw,2.4rem); }
        p { margin: 0; line-height:1.65; }
        .subtitle { color:#e2e8f0; max-width:700px; }
        .actions { margin-top:18px; display:flex; gap:10px; flex-wrap:wrap; }
        .btn { border:0; border-radius:12px; padding:12px 16px; font-weight:700; cursor:pointer; text-decoration:none; display:inline-block; transition: transform .15s ease, box-shadow .2s ease, opacity .2s ease; }
        .btn:hover { transform: translateY(-1px); }
        .btn-primary { background:#fff; color:#1e3a8a; box-shadow: 0 8px 18px rgba(30,58,138,.25); }
        .btn-secondary { background:#0f172a; color:#fff; }
        section { margin-top: 28px; }
        .section-title { margin:0 0 14px; font-size:1.35rem; }
        .grid { display:grid; gap:12px; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); }
        .card { background: var(--card); border:1px solid #e2e8f0; border-radius:14px; padding:16px; box-shadow: 0 8px 20px rgba(2,6,23,.05); }
        .info { background:#fff; border-radius:14px; border:1px solid #e2e8f0; padding:18px; }
        footer { margin-top:32px; display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; }
        .muted { color:var(--muted); }
        @media (max-width: 600px) {
          .wrap { padding: 18px 14px 30px; }
          .hero { padding: 24px 16px; border-radius:16px; }
        }
      </style>
    </head>
    <body>
      <div class='wrap'>
        <header>
          <div class='brand'>Uchiha Developer</div>
          <a class='btn btn-secondary' href='https://t.me' target='_blank' rel='noopener noreferrer'>Contact Support</a>
        </header>

        <section class='hero'>
          <h1>Secure File Access & Verification</h1>
          <p class='subtitle'>Secure file access and verification system with fast delivery and protected content.</p>
          <div class='actions'>
            <a class='btn btn-primary' href='/verify/sample-token'>Start Verification</a>
            <a class='btn btn-secondary' href='https://t.me' target='_blank' rel='noopener noreferrer'>Contact Support</a>
          </div>
        </section>

        <section>
          <h2 class='section-title'>Features</h2>
          <div class='grid'>
            <div class='card'>✔ Secure File Access</div>
            <div class='card'>✔ Fast Verification</div>
            <div class='card'>✔ Protected Content Delivery</div>
            <div class='card'>✔ Mobile Friendly</div>
          </div>
        </section>

        <section id='how-it-works' class='info'>
          <h2 class='section-title'>How It Works</h2>
          <p class='muted'>Users receive a protected verification link for a specific file token. They complete quick verification steps, then the system unlocks file delivery. Ads help maintain hosting, bandwidth, and bot infrastructure while keeping access flow available.</p>
        </section>

        <footer>
          <span class='muted'>Protected verification flow for secure file delivery.</span>
          <a class='btn btn-secondary' href='https://t.me' target='_blank' rel='noopener noreferrer'>Telegram</a>
        </footer>
      </div>
    </body>
    </html>
    """
    return web.Response(text=html, content_type="text/html")


@routes.get("/favicon.ico", allow_head=True)
async def favicon_handler(request):
    return web.Response(
        body=(
            b"\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00 \x00(\x01\x00\x00\x16\x00\x00\x00"
            b"(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00 \x00\x00\x00\x00\x00\x00\x01"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff"
            b"\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\x00\x00"
            b"\xff\xff\x00\x00\xff\xff\x00\x00\xff\xff\x00\x00\xff\xff\x00\x00\xff\xff\x00\x00"
            b"\xff\xff\x00\x00\xff\xff\x00\x00\xff\xff\x00\x00\xff\xff\x00\x00\xff\xff\x00\x00"
            b"\xff\xff\x00\x00\xff\xff\x00\x00\xff\xff\x00\x00\xff\xff\x00\x00"
        ),
        content_type="image/x-icon",
    )


@routes.get("/verify/{token}")
async def verify_token(request):
    return await verification_page(request)


@routes.get("/rewarded_popup_done/{token}")
async def rewarded_popup_done_route(request):
    return await rewarded_popup_done(request)


@routes.get("/miniapp/interstitial/{token}")
async def interstitial_route(request):
    return await interstitial_miniapp(request)


@routes.get("/interstitial_done/{token}")
async def interstitial_done_route(request):
    return await interstitial_done(request)


@routes.get("/complete/{token}")
async def complete_route(request):
    return await complete(request)


@routes.post("/api/verification/{token}/start-ad")
async def start_ad_route(request):
    return await start_ad(request)


@routes.post("/api/verification/{token}/complete-ad")
async def complete_ad_route(request):
    return await complete_ad(request)
