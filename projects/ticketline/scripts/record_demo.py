"""Record the Ticketline demo video against the public instance."""
import os
import shutil

from playwright.sync_api import sync_playwright

URL = os.getenv("DEMO_URL", "https://ticketline.5-222-1-215.sslip.io/")
OUT_DIR = "/tmp/opencode/ticketline-rec"
VIDEO_SIZE = {"width": 1280, "height": 720}

CAPTION_JS = """
(text) => {
  let el = document.getElementById('demo-caption');
  if (!el) {
    el = document.createElement('div');
    el.id = 'demo-caption';
    el.style.cssText = [
      'position:fixed', 'left:50%', 'bottom:22px', 'transform:translateX(-50%)',
      'background:rgba(16,24,40,.9)', 'color:#fff', 'z-index:9999',
      'font:600 15px/1.45 Inter,system-ui,sans-serif', 'padding:10px 18px',
      'border-radius:10px', 'max-width:82%', 'text-align:center',
      'box-shadow:0 8px 24px rgba(0,0,0,.3)'
    ].join(';');
    document.body.appendChild(el);
  }
  el.textContent = text;
  el.style.opacity = text ? '1' : '0';
}
"""


def caption(page, text, hold=0):
    page.evaluate(CAPTION_JS, text)
    if hold:
        page.wait_for_timeout(hold)


def click_text(page, pattern):
    return page.evaluate(
        """(src) => {
            const rx = new RegExp(src, 'i');
            const b = [...document.querySelectorAll('button')].find(
              (x) => rx.test(x.innerText || '') && x.offsetParent && !x.disabled
            );
            if (b) { b.click(); return true; }
            return false;
        }""",
        pattern,
    )


shutil.rmtree(OUT_DIR, ignore_errors=True)
os.makedirs(OUT_DIR, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path="/usr/bin/google-chrome",
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--hide-scrollbars"],
    )
    context = browser.new_context(
        viewport=VIDEO_SIZE,
        record_video_dir=OUT_DIR,
        record_video_size=VIDEO_SIZE,
        device_scale_factor=1,
    )
    page = context.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_selector("button.primary", timeout=25000)
    page.wait_for_timeout(1200)
    caption(page, "Personal demo project — fictional data", 2400)

    caption(page, "1. Technician records the job")
    click_text(page, "Create draft ticket")
    page.wait_for_timeout(2400)
    caption(page, "Line items with exact prices; total computed in cents", 2200)

    caption(page, "2. Submit for review")
    click_text(page, "Submit for review")
    page.wait_for_timeout(2400)

    caption(page, "3. Reviewer approves")
    page.select_option(".role select", "user_review")
    page.wait_for_timeout(2200)
    page.evaluate("() => document.querySelector('.row')?.click()")
    page.wait_for_timeout(1400)
    click_text(page, "^Approve$")
    page.wait_for_timeout(3500)

    caption(page, "4. Invoice is issued and numbered")
    issued = click_text(page, "Issue demo invoice")
    if not issued:
        page.wait_for_timeout(2000)
        issued = click_text(page, "Issue demo invoice")
    page.wait_for_timeout(3500)
    caption(page, "A real PDF with a frozen snapshot of the client and items", 2600)

    video = page.video
    context.close()
    browser.close()
    path = video.path()
    print(f"video: {path}")
    print(f"size: {os.path.getsize(path)} bytes")
