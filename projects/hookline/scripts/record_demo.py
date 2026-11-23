"""Record the Hookline demo video against the public instance."""
import os
import shutil

from playwright.sync_api import sync_playwright

URL = os.getenv("DEMO_URL", "https://hookline.5-222-1-215.sslip.io/")
OUT_DIR = "/tmp/opencode/hookline-rec"
VIDEO_SIZE = {"width": 1280, "height": 720}

CAPTION_JS = """
(text) => {
  let el = document.getElementById('demo-caption');
  if (!el) {
    el = document.createElement('div');
    el.id = 'demo-caption';
    el.style.cssText = [
      'position:fixed', 'left:50%', 'bottom:24px', 'transform:translateX(-50%)',
      'background:rgba(16,24,40,.9)', 'color:#fff', 'z-index:9999',
      'font:600 15px/1.45 Inter,system-ui,sans-serif', 'padding:10px 18px',
      'border-radius:10px', 'max-width:80%', 'text-align:center',
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


def click_scenario(page, index):
    page.evaluate(f"() => document.querySelectorAll('button.scenario')[{index}]?.click()")
    page.wait_for_timeout(2200)
    # Select the newest execution so the detail panel is visible in the video.
    page.evaluate("() => document.querySelector('.row')?.click()")
    page.wait_for_timeout(600)


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
    page.wait_for_selector("button.scenario", timeout=20000)
    page.wait_for_timeout(1200)
    caption(page, "Personal demo project — fictional data", 2200)

    caption(page, "1. A signed webhook triggers a three-step flow")
    click_scenario(page, 0)
    page.wait_for_timeout(2400)
    caption(page, "The event is stored before processing; all steps succeed", 2200)

    caption(page, "2. Destination fails twice — retries recover")
    click_scenario(page, 1)
    page.wait_for_timeout(7000)
    caption(page, "Succeeded after retries. The reservation exists once.", 2600)

    caption(page, "3. A permanent failure stops the flow")
    click_scenario(page, 2)
    page.wait_for_timeout(2400)
    caption(page, "Dead-lettered with the failing step and the HTTP 422.", 2600)

    caption(page, "4. The same event delivered twice")
    click_scenario(page, 3)
    page.wait_for_timeout(2400)
    caption(page, "One execution, one business action.", 2400)

    caption(page, "5. Replay after fixing the cause")
    page.evaluate("() => { const rows=[...document.querySelectorAll('.row')]; rows.find(r=>r.innerText.includes('DEAD'))?.click(); }")
    page.wait_for_timeout(1200)
    page.evaluate("() => { const b=[...document.querySelectorAll('button')].find(x=>x.innerText.includes('Replay execution')); if(b) b.click(); }")
    page.wait_for_timeout(3500)
    caption(page, "New execution for the same stored event — history preserved.", 2600)

    video = page.video
    context.close()
    browser.close()
    path = video.path()
    print(f"video: {path}")
    print(f"size: {os.path.getsize(path)} bytes")
