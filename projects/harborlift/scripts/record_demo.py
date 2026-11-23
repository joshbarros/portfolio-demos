"""Record the Harborlift recorded-run replay with captions."""
import os
import shutil

from playwright.sync_api import sync_playwright

URL = os.getenv("DEMO_URL", "https://harborlift.5-222-1-215.sslip.io/replay.html")
OUT_DIR = "/tmp/opencode/harborlift-rec"
SIZE = {"width": 1280, "height": 800}

CAPTION = """
(text) => {
  let el = document.getElementById('demo-caption');
  if (!el) {
    el = document.createElement('div');
    el.id = 'demo-caption';
    el.style.cssText = [
      'position:fixed','left:50%','bottom:22px','transform:translateX(-50%)',
      'background:rgba(16,24,40,.92)','color:#fff','z-index:9999',
      'font:600 15px/1.45 Inter,system-ui,sans-serif','padding:10px 18px',
      'border-radius:10px','max-width:84%','text-align:center',
      'box-shadow:0 8px 24px rgba(0,0,0,.3)'
    ].join(';');
    document.body.appendChild(el);
  }
  el.textContent = text;
  el.style.opacity = text ? '1' : '0';
}
"""


def caption(page, text, hold=0):
    page.evaluate(CAPTION, text)
    if hold:
        page.wait_for_timeout(hold)


shutil.rmtree(OUT_DIR, ignore_errors=True)
os.makedirs(OUT_DIR, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path="/usr/bin/google-chrome",
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--hide-scrollbars"],
    )
    context = browser.new_context(viewport=SIZE, record_video_dir=OUT_DIR, record_video_size=SIZE, device_scale_factor=1)
    page = context.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_selector("#steps tr", timeout=20000)
    page.wait_for_timeout(800)
    caption(page, "Personal demo project — recorded migration run", 3200)
    caption(page, "Snapshot, restore and a versioned schema migration", 6500)
    caption(page, "Integrity validated: checksum, counts, nulls, index", 6500)
    caption(page, "Cutover; writes rejected during the freeze window", 6500)
    caption(page, "Rollback verified — the source accepts writes again", 6500)
    video = page.video
    context.close()
    browser.close()
    print(video.path())
