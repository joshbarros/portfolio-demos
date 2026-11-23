"""Record the Vaultgate demo: authorized access -> cross-tenant block -> other org."""
import os
import shutil

from playwright.sync_api import sync_playwright

URL = os.getenv("DEMO_URL", "https://vaultgate.5-222-1-215.sslip.io/")
OUT = "/tmp/opencode/vaultgate-rec"
SIZE = {"width": 1280, "height": 800}

CAPTION = """
(text) => {
  let el = document.getElementById('demo-caption');
  if (!el) {
    el = document.createElement('div'); el.id = 'demo-caption';
    el.style.cssText = ['position:fixed','left:50%','bottom:22px','transform:translateX(-50%)',
      'background:rgba(16,24,40,.92)','color:#fff','z-index:9999','font:600 15px/1.45 Inter,system-ui,sans-serif',
      'padding:10px 18px','border-radius:10px','max-width:84%','text-align:center',
      'box-shadow:0 8px 24px rgba(0,0,0,.3)'].join(';');
    document.body.appendChild(el);
  }
  el.textContent = text; el.style.opacity = text ? '1' : '0';
}
"""


def caption(page, text, hold=0):
    page.evaluate(CAPTION, text)
    if hold:
        page.wait_for_timeout(hold)


def click(page, text):
    page.evaluate(
        """(t) => { const b=[...document.querySelectorAll('button')].find(x => new RegExp(t,'i').test(x.innerText||'') && x.offsetParent && !x.disabled); if (b) b.click(); }""",
        text,
    )


shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True,
                                args=["--no-sandbox", "--disable-dev-shm-usage", "--hide-scrollbars"])
    context = browser.new_context(viewport=SIZE, record_video_dir=OUT, record_video_size=SIZE, device_scale_factor=1)
    page = context.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_selector("button.primary", timeout=25000)
    page.wait_for_timeout(1200)
    caption(page, "Personal demo project — two fictional organizations", 2600)
    caption(page, "Sign in as Alpha Freight", 2600)
    click(page, "Sign in")
    page.wait_for_timeout(3000)
    caption(page, "Only Alpha's two files are listed; the tenant comes from the session", 3200)
    caption(page, "Attempt to read Beta's file by id", 2000)
    click(page, "Attempt cross-tenant access")
    page.wait_for_timeout(2600)
    caption(page, "Blocked with 404 by row-level security; the denial is audited", 3400)
    caption(page, "Switch organization: sign in as Beta Clinic", 2200)
    click(page, "Sign out")
    page.wait_for_timeout(1200)
    page.select_option("select", "user_beta_user")
    page.wait_for_timeout(600)
    click(page, "Sign in")
    page.wait_for_timeout(3000)
    caption(page, "Beta sees only its own file — no browser parameter can change that", 3600)
    video = page.video
    context.close()
    browser.close()
    print(video.path())
