"""Record the demo video against the public instance, with burned-in captions."""
import os
import shutil

from playwright.sync_api import sync_playwright

URL = os.getenv("DEMO_URL", "https://northstar.5-222-1-215.sslip.io/")
OUT_DIR = "/tmp/opencode/rec"
VIDEO_SIZE = {"width": 1280, "height": 720}

CAPTION_JS = """
(text) => {
  let el = document.getElementById('demo-caption');
  if (!el) {
    el = document.createElement('div');
    el.id = 'demo-caption';
    el.style.cssText = [
      'position:fixed', 'left:50%', 'bottom:96px', 'transform:translateX(-50%)',
      'background:rgba(16,24,40,.88)', 'color:#fff', 'z-index:9999',
      'font:600 15px/1.45 Inter,system-ui,-apple-system,sans-serif',
      'padding:9px 16px', 'border-radius:10px', 'max-width:78%',
      'text-align:center', 'box-shadow:0 8px 24px rgba(0,0,0,.28)',
      'transition:opacity .35s ease', 'pointer-events:none'
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
    page.goto(URL, wait_until="networkidle")
    page.wait_for_timeout(1200)
    caption(page, "Personal demo project — fictional company, fictional data", 3200)

    # Scene A
    caption(page, "1. Answer with a verifiable citation")
    page.get_by_role("button", name="Answer with source").click()
    page.wait_for_selector("details.citation summary")
    page.wait_for_timeout(2600)
    caption(page, "The citation opens to the source document, excerpt and update date")
    page.locator("details.citation summary").first.click()
    page.wait_for_timeout(3400)
    page.locator("details.citation summary").first.click()
    page.wait_for_timeout(500)

    # Scene B
    caption(page, "2. No evidence in the knowledge base → explicit abstention")
    page.get_by_role("button", name="Abstain honestly").click()
    page.wait_for_selector(".flag-abstain")
    page.wait_for_timeout(3400)

    # Scene C
    caption(page, "3. A tool call: the ticket is created by the app")
    page.get_by_role("button", name="Auditable action").click()
    page.wait_for_selector(".flag-tool")
    page.wait_for_timeout(2400)
    caption(page, "The ticket appears in the tenant's list")
    page.get_by_role("tab", name="Tickets").click()
    page.wait_for_timeout(2400)
    caption(page, "Audit log: sanitized arguments and the tool result")
    page.get_by_role("tab", name="Audit").click()
    page.wait_for_timeout(3000)

    # Scene D
    caption(page, "Tenant isolation: wrong tenant → no answer")
    page.get_by_role("button", name="Tenant isolation").click()
    page.wait_for_selector(".flag-abstain")
    page.wait_for_timeout(2800)
    caption(page, "Same question, correct tenant → grounded answer")
    page.locator("button.tenant").nth(1).click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Tenant isolation").click()
    page.wait_for_selector("details.citation summary")
    page.wait_for_timeout(3600)

    video = page.video
    context.close()
    browser.close()
    path = video.path()
    print(f"video: {path}")
    print(f"size: {os.path.getsize(path)} bytes")
