from datetime import datetime, timezone
import logging

from aiohttp import ClientSession, web

from config import WEB_BASE_URL
from database.ads_database import country_to_tier, get_ad_settings, record_ad_completion
from verification_system import (
    can_start_ad_attempt,
    complete_step,
    get_next_required_step,
    get_token_or_none,
    register_page_visit,
)

LOGGER = logging.getLogger(__name__)


def _tg_open_link(path: str) -> str:
    if WEB_BASE_URL:
        return f"{WEB_BASE_URL}{path}"
    return path


def _seconds_until(dt: datetime) -> int:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return max(0, int((dt - now).total_seconds()))


def _extract_ip(request: web.Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP", "").strip()
    if real_ip:
        return real_ip
    return (request.remote or "").strip()


async def _country_from_ip(ip_address: str) -> str:
    if not ip_address:
        return "Unknown"
    try:
        async with ClientSession() as session:
            async with session.get(f"http://ip-api.com/json/{ip_address}?fields=status,countryCode", timeout=4) as resp:
                data = await resp.json(content_type=None)
                if data.get("status") == "success" and data.get("countryCode"):
                    return str(data.get("countryCode")).upper()
    except Exception:
        pass
    return "Unknown"


async def verification_page(request: web.Request) -> web.Response:
    token = request.match_info.get("token", "")
    data = await register_page_visit(token)
    if not data:
        return web.Response(text="Verification token invalid, expired, or blocked.", status=400)

    settings = await get_ad_settings()
    required = data.get("required_steps", [])
    if not required or not settings.get("ads_enabled"):
        await complete_step(token, "rewarded_popup")
        await complete_step(token, "interstitial")
        raise web.HTTPFound(_tg_open_link(f"/complete/{token}"))

    ad_ready_in = _seconds_until(data.get("ad_available_at", datetime.utcnow()))
    progress = int((len(data.get("completed_steps", [])) / max(1, len(required))) * 100)
    interstitial_zone = "10739699"
    configured_popup_zone = (settings.get("rewarded_popup_zone", "") or "").strip()
    popup_zone = configured_popup_zone or interstitial_zone
    popup_fn_name = f"show_{popup_zone}"
    needs_separate_popup_sdk = bool(configured_popup_zone) and configured_popup_zone != interstitial_zone
    popup_sdk_tag = (
        f"<script src='https://libtl.com/sdk.js' data-zone='{popup_zone}' data-sdk='{popup_fn_name}'></script>"
        if needs_separate_popup_sdk
        else ""
    )
    token_user_id = data.get("user_id")

    html = f"""
    <!doctype html>
    <html lang='en'>
    <head>
      <meta charset='utf-8' />
      <meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover' />
      <meta name='theme-color' content='#111827' />
      <title>File Verification Required</title>
      <script src='https://telegram.org/js/telegram-web-app.js'></script>
      <script src='https://libtl.com/sdk.js' data-zone='10739699' data-sdk='show_10739699'></script>
      {popup_sdk_tag}
      <style>
        :root {{ --card-bg: rgba(255,255,255,.85); --text:#0f172a; --muted:#475569; --primary:#2563eb; --accent:#7c3aed; }}
        @media (prefers-color-scheme: dark) {{
          :root {{ --card-bg: rgba(15,23,42,.86); --text:#e2e8f0; --muted:#94a3b8; --primary:#60a5fa; --accent:#a78bfa; }}
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin:0; min-height:100vh; display:grid; place-items:center; padding:20px;
          font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          color: var(--text);
          background: linear-gradient(135deg, #dbeafe, #ede9fe 60%, #bfdbfe);
        }}
        .layout {{ width:min(760px,100%); margin:0 auto; display:grid; gap:16px; align-items:center; }}
        .ad-slot {{ width:100%; min-height:90px; border-radius:14px; background:rgba(148,163,184,.16); display:flex; align-items:center; justify-content:center; overflow:hidden; padding:8px; }}
        .ad-slot > div {{ width:100%; display:flex; justify-content:center; }}
        .card {{
          width:min(460px,100%); margin:0 auto; border-radius:22px; padding:22px;
          background:var(--card-bg); backdrop-filter: blur(12px);
          box-shadow: 0 12px 40px rgba(2,6,23,.2);
          animation: in .45s ease;
        }}
        @keyframes in {{ from {{ transform:translateY(8px);opacity:0; }} to {{ transform:translateY(0);opacity:1; }} }}
        h1 {{ margin:0 0 8px; font-size:24px; }}
        .sub {{ margin:0 0 16px; color:var(--muted); font-size:14px; }}
        .progress {{ height:10px; border-radius:999px; background:rgba(148,163,184,.35); overflow:hidden; margin:10px 0 14px; }}
        .bar {{ height:100%; width:{progress}%; background:linear-gradient(90deg,var(--primary),var(--accent)); transition:width .4s ease; }}
        .steps {{ margin:0 0 18px; padding-left:18px; color:var(--muted); font-size:14px; line-height:1.7; }}
        .btn {{
          width:100%; border:0; border-radius:14px; padding:14px 16px; font-weight:700;
          background:linear-gradient(90deg,var(--primary),var(--accent)); color:#fff; cursor:pointer;
          transition:transform .15s ease, opacity .15s ease, box-shadow .2s;
          box-shadow:0 8px 20px rgba(37,99,235,.35);
        }}
        .btn:active {{ transform:scale(.98); }}
        .btn[disabled] {{ opacity:.55; cursor:not-allowed; box-shadow:none; }}
        .row {{ display:flex; align-items:center; justify-content:space-between; gap:8px; margin-top:12px; }}
        .badge {{ font-size:12px; color:var(--muted); }}
        .status {{ font-size:13px; color:var(--muted); min-height:20px; }}
        .footer {{ text-align:center; font-size:12px; color:var(--muted); margin-top:16px; }}
        .retry {{ margin-top:10px; display:none; text-align:center; color:var(--primary); font-size:13px; cursor:pointer; }}
      </style>
    </head>
    <body>
      <div class='layout'>
        <div class='ad-slot'>
          <script async='async' data-cfasync='false' src='https://pl29308130.profitablecpmratenetwork.com/7b19338d1a399fee5d73112abab706c9/invoke.js'></script>
          <div id='container-7b19338d1a399fee5d73112abab706c9'></div>
        </div>

        <div class='card'>
        <h1>File Verification Required</h1>
        <p class='sub'>Complete a quick verification to unlock your file.</p>

        <div class='progress'><div id='bar' class='bar'></div></div>
        <ol class='steps'>
          <li>Step 1: Interstitial ad</li>
          <li>Step 2: Rewarded Popup ad</li>
          <li>Unlock content</li>
        </ol>

        <button class='btn' id='interstitialBtn' disabled>Preparing Interstitial… <span id='count'>{ad_ready_in}</span>s</button>
        <button class='btn' id='rewardedPopupBtn' style='margin-top:10px;opacity:.65;' disabled>Step 2: Open Rewarded Popup</button>
        <div class='row'>
          <div class='status' id='status'>Waiting for cooldown...</div>
          <div class='badge'>Protected by secure verification</div>
        </div>
        <div id='retry' class='retry'>Retry verification</div>

        <div class='footer'>This helps us keep the bot free.</div>
        </div>

        <div class='ad-slot'>


        </div>
      </div>

      <script>
        (function() {{
          const token = {token!r};
          const requiredSteps = {required!r};
          const tokenUserId = {token_user_id!r};
          const adFnName = 'show_10739699';
          const popupFnName = {popup_fn_name!r};
          const interstitialBtn = document.getElementById('interstitialBtn');
          const rewardedPopupBtn = document.getElementById('rewardedPopupBtn');
          const count = document.getElementById('count');
          const status = document.getElementById('status');
          const retry = document.getElementById('retry');
          const bar = document.getElementById('bar');

          const tgWebApp = (window.Telegram && Telegram.WebApp) ? Telegram.WebApp : null;
          if (tgWebApp) {{ tgWebApp.ready(); tgWebApp.expand(); }}

          let remaining = {ad_ready_in};
          let flowLocked = false;
          let adPreloaded = false;

          function log(msg, data) {{
            if (data !== undefined) console.info('[verify]', msg, data);
            else console.info('[verify]', msg);
          }}
          function setError(code) {{ status.textContent = 'Error: ' + code; }}
          function setProgress(pct) {{ bar.style.width = Math.max(5, Math.min(100, pct)) + '%'; }}

          const timer = setInterval(() => {{
            if (remaining <= 0) {{
              clearInterval(timer);
              interstitialBtn.textContent = 'Watch Ad & Continue';
              if (adPreloaded) {{
                interstitialBtn.disabled = false;
                status.textContent = 'Step 1 ready.';
              }} else {{
                status.textContent = 'Preparing ad...';
              }}
              return;
            }}
            remaining -= 1;
            count.textContent = remaining;
          }}, 1000);

          async function api(url, payload) {{
            log('api', {{ url: url, payload: payload }});
            const res = await fetch(url, {{
              method: 'POST',
              headers: {{ 'Content-Type': 'application/json' }},
              body: JSON.stringify(payload || {{}})
            }});
            const body = await res.json().catch(() => ({{ ok: false, error: 'invalid_json' }}));
            if (!res.ok || !body.ok) throw new Error((body && body.error) ? body.error : 'request_failed');
            return body;
          }}

          async function waitForSdk(fnName) {{
            const started = Date.now();
            while (Date.now() - started < 12000) {{
              if (typeof window[fnName] === 'function') {{
                log('SDK Loaded', fnName);
                log('Ad Function Found', fnName);
                return;
              }}
              await new Promise(r => setTimeout(r, 250));
            }}
            log('Ad Failed', 'function_not_found:' + fnName);
            throw new Error('sdk_not_loaded');
          }}

          async function preloadAd() {{
            await waitForSdk(adFnName);
            status.textContent = 'Loading ad unit...';
            try {{
              await window[adFnName]({{ type: 'preload', ymid: tokenUserId }});
              adPreloaded = true;
              log('Preload Success');
              if (remaining <= 0) {{
                interstitialBtn.disabled = false;
                status.textContent = 'Step 1 ready.';
              }}
            }} catch (_) {{
              log('Preload Failed');
              throw new Error('ad_failed');
            }}
          }}

          async function runRewardedInterstitial() {{
            await waitForSdk(adFnName);
            if (!adPreloaded) throw new Error('ad_failed');
            log('Ad Started');
            try {{
              await window[adFnName]({{ ymid: tokenUserId }});
              log('Ad Completed');
            }} catch (_) {{
              log('Ad Failed');
              throw new Error('ad_failed');
            }}
          }}

          async function runRewardedPopup() {{
            await waitForSdk(popupFnName);
            log('Popup Ad Started');
            try {{
              await window[popupFnName]({{ type: 'pop', ymid: tokenUserId }});
              log('Popup Ad Completed');
            }} catch (_) {{
              log('Popup Ad Failed');
              throw new Error('ad_failed');
            }}
          }}

          async function handleStep(step) {{
            const payload = {{
              step: step,
              tg_init_data: tgWebApp ? tgWebApp.initData : '',
              tg_user_id: tgWebApp && tgWebApp.initDataUnsafe && tgWebApp.initDataUnsafe.user ? tgWebApp.initDataUnsafe.user.id : null
            }};

            if (step === 'interstitial') {{
              await api('/api/verification/' + token + '/start-ad', payload);
              status.textContent = 'Loading rewarded ad...';
              await runRewardedInterstitial();
            }} else {{
              // Rewarded Popup must be triggered synchronously inside the click
              // gesture, before any await, or browsers/Telegram WebView will
              // block the popup from opening.
              status.textContent = 'Opening rewarded popup...';
              const popupPromise = runRewardedPopup();
              await api('/api/verification/' + token + '/start-ad', payload);
              await popupPromise;
            }}

            await api('/api/verification/' + token + '/complete-ad', {{ step: step, ad_completed: true }});
          }}

          function showRetry(step) {{
            retry.style.display = 'block';
            retry.onclick = () => {{
              retry.style.display = 'none';
              startFlow(step);
            }};
          }}

          async function startFlow(step) {{
            if (flowLocked) return;
            flowLocked = true;
            retry.style.display = 'none';
            interstitialBtn.disabled = true;
            rewardedPopupBtn.disabled = true;
            setProgress(step === 'interstitial' ? 25 : 70);

            try {{
              await handleStep(step);
              if (step === 'interstitial') {{
                setProgress(60);
                rewardedPopupBtn.disabled = false;
                rewardedPopupBtn.style.opacity = '1';
                status.textContent = 'Step 1 complete. Open the rewarded popup.';
              }} else {{
                setProgress(100);
                status.textContent = 'Verification complete. Redirecting...';
                window.location.href = '/complete/' + token;
              }}
            }} catch (e) {{
              const code = (e && e.message) ? e.message : 'ad_failed';
              setError(code);
              log('Error', code);
              interstitialBtn.disabled = false;
              if (step === 'rewarded_popup') rewardedPopupBtn.disabled = false;
              showRetry(step);
            }} finally {{
              flowLocked = false;
            }}
          }}

          interstitialBtn.onclick = () => startFlow('interstitial');
          rewardedPopupBtn.onclick = () => startFlow('rewarded_popup');
          setProgress(Math.min(20, requiredSteps.length ? 100 : 0));
          preloadAd().catch((e) => {{
            setError(e.message || 'ad_failed');
            showRetry('interstitial');
          }});
        }})();
      </script>
    </body>
    </html>
    """
    return web.Response(text=html, content_type="text/html")


async def start_ad(request: web.Request) -> web.Response:
    token = request.match_info.get("token", "")
    payload = await request.json() if request.can_read_body else {}
    step = payload.get("step", "").strip().lower()
    if step not in {"interstitial", "rewarded_popup"}:
        return web.json_response({"ok": False, "error": "invalid_step"}, status=400)

    LOGGER.info("start-ad token=%s step=%s", token, step)
    data = await can_start_ad_attempt(token)
    if not data:
        LOGGER.info("start-ad denied token=%s reason=token_invalid_or_blocked", token)
        return web.json_response({"ok": False, "error": "token_invalid_or_blocked"}, status=400)

    next_step = get_next_required_step(data)
    if next_step and step != next_step:
        LOGGER.info("start-ad denied token=%s reason=wrong_step expected=%s got=%s", token, next_step, step)
        return web.json_response({"ok": False, "error": f"step_order_invalid_expected_{next_step}"}, status=409)

    tg_user_id = payload.get("tg_user_id")
    token_user_id = data.get("user_id")
    if tg_user_id and token_user_id and int(tg_user_id) != int(token_user_id):
        LOGGER.info("start-ad denied token=%s reason=user_mismatch", token)
        return web.json_response({"ok": False, "error": "user_mismatch"}, status=403)

    if _seconds_until(data.get("ad_available_at", datetime.utcnow())) > 0:
        LOGGER.info("start-ad denied token=%s reason=cooldown", token)
        return web.json_response({"ok": False, "error": "cooldown_not_ready"}, status=429)

    LOGGER.info("start-ad ok token=%s step=%s attempts=%s", token, step, data.get("ad_attempts", 0))
    return web.json_response({"ok": True, "attempts": data.get("ad_attempts", 0), "step": step})


async def complete_ad(request: web.Request) -> web.Response:
    token = request.match_info.get("token", "")
    data = await get_token_or_none(token)
    if not data:
        return web.json_response({"ok": False, "error": "token_invalid"}, status=400)

    payload = await request.json() if request.can_read_body else {}
    step = payload.get("step", "").strip().lower()
    if step not in {"interstitial", "rewarded_popup"}:
        return web.json_response({"ok": False, "error": "invalid_step"}, status=400)
    if not payload.get("ad_completed"):
        return web.json_response({"ok": False, "error": "ad_incomplete"}, status=400)

    LOGGER.info("complete-ad token=%s step=%s", token, step)
    next_step = get_next_required_step(data)
    if next_step and step != next_step:
        LOGGER.info("complete-ad denied token=%s reason=wrong_step expected=%s got=%s", token, next_step, step)
        return web.json_response({"ok": False, "error": f"step_order_invalid_expected_{next_step}"}, status=409)

    required = data.get("required_steps", [])
    if step not in required:
        LOGGER.info("complete-ad denied token=%s reason=step_not_required step=%s", token, step)
        return web.json_response({"ok": False, "error": "step_not_required"}, status=400)

    updated = await complete_step(token, step)
    if not updated:
        LOGGER.info("complete-ad denied token=%s reason=complete_step_failed", token)
        return web.json_response({"ok": False, "error": "complete_step_failed"}, status=400)

    if not get_next_required_step(updated):
        country_code = request.headers.get("CF-IPCountry", "").strip().upper()
        if not country_code:
            country_code = await _country_from_ip(_extract_ip(request))
        await record_ad_completion(
            token=token,
            user_id=int(updated.get("user_id", 0)),
            bot_id=updated.get("bot_id"),
            file_id=updated.get("file_id", updated.get("base64_payload", "")),
            country=country_code,
        )
        LOGGER.info(
            "ad-completion tracked token=%s user_id=%s country=%s tier=%s",
            token,
            updated.get("user_id"),
            country_code,
            country_to_tier(country_code),
        )

    LOGGER.info("complete-ad ok token=%s step=%s", token, step)
    return web.json_response({"ok": True})


async def rewarded_popup_done(request: web.Request) -> web.Response:
    token = request.match_info.get("token", "")
    data = await complete_step(token, "rewarded_popup")
    if not data:
        return web.Response(text="Invalid token.", status=400)
    raise web.HTTPFound(_tg_open_link(f"/verify/{token}"))


async def interstitial_miniapp(request: web.Request) -> web.Response:
    raise web.HTTPFound(_tg_open_link(f"/verify/{request.match_info.get('token', '')}"))


async def interstitial_done(request: web.Request) -> web.Response:
    token = request.match_info.get("token", "")
    data = await complete_step(token, "interstitial")
    if not data:
        return web.Response(text="Invalid token.", status=400)
    raise web.HTTPFound(_tg_open_link(f"/complete/{token}"))


async def complete(request: web.Request) -> web.Response:
    token = request.match_info.get("token", "")
    data = await get_token_or_none(token)
    if not data:
        return web.Response(text="Token expired. Re-open your original bot link.", status=400)
    deep_link = f"https://t.me/{request.app['bot_username']}?start=unlock_{token}"
    html = f"""
    <html><body style='font-family:sans-serif;padding:20px;'>
    <h3>Verification complete</h3>
    <p>Returning you to the bot now...</p>
    <a href='{deep_link}'>Return to bot and unlock file</a>
    <script>setTimeout(function(){{window.location.href={deep_link!r};}}, 1200);</script>
    </body></html>
    """
    return web.Response(text=html, content_type="text/html")
