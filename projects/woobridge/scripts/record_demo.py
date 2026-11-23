"""Record the WooBridge demo: source change -> sync -> WooCommerce updated."""
import os
import shutil
import subprocess

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8080"
OUT = "/tmp/opencode/woobridge-rec"
SIZE = {"width": 1280, "height": 800}

CAPTION = """
(text) => {
  let el = document.getElementById('demo-caption');
  if (!el) {
    el = document.createElement('div'); el.id='demo-caption';
    el.style.cssText = ['position:fixed','left:50%','bottom:22px','transform:translateX(-50%)',
      'background:rgba(16,24,40,.92)','color:#fff','z-index:99999','font:600 15px/1.45 Inter,system-ui,sans-serif',
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


def click_text(page, text):
    page.evaluate(
        """(t) => { const b=[...document.querySelectorAll('button,a,input[type=submit]')].find(x => new RegExp(t,'i').test((x.innerText||x.value||'')) && x.offsetParent); if (b) b.click(); }""",
        text,
    )


shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True,
                                args=["--no-sandbox", "--disable-dev-shm-usage", "--hide-scrollbars"])
    context = browser.new_context(viewport=SIZE, record_video_dir=OUT, record_video_size=SIZE, device_scale_factor=1)
    page = context.new_page()
    page.goto(f"{URL}/wp-login.php", wait_until="domcontentloaded")
    page.fill("#user_login", "admin")
    page.fill("#user_pass", "demo")
    page.evaluate("() => document.querySelector('#wp-submit')?.click()")
    page.wait_for_timeout(3000)
    page.goto(f"{URL}/wp-admin/admin.php?page=woobridge", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    caption(page, "Personal demo project — WooCommerce + fictional catalog API", 2800)
    caption(page, "Admin settings: API URL, token, page size, deletion policy", 3000)

    caption(page, "The source price changes", 1200)
    subprocess.run(["curl", "-s", "-X", "POST", "http://127.0.0.1:4011/_control",
                    "-H", "content-type: application/json",
                    "-d", '{"update":{"external_id":"ext_1001","price":"64.90"}}'], capture_output=True)

    caption(page, "Sync now: pagination, upsert by external id, lock and logs", 1600)
    click_text(page, "Sync now")
    page.wait_for_timeout(3500)
    caption(page, "Updated, not duplicated; every step is in the log", 3000)

    caption(page, "WooCommerce shows the product with the new price", 1200)
    page.goto(f"{URL}/wp-admin/edit.php?post_type=product", wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    caption(page, "Harbor Lamp at 64.90, synced from the external id", 3200)

    video = page.video
    context.close()
    browser.close()
    print(video.path())
