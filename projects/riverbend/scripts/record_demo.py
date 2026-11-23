"""Record the Riverbend demo: load -> controlled error -> correction -> updated indicators."""
import base64
import os
import shutil
import subprocess

from playwright.sync_api import sync_playwright

URL = os.getenv("DEMO_URL", "https://riverbend.5-222-1-215.sslip.io/")
HOST = os.getenv("RIVERBEND_HOST", "root@5.222.1.215")
CONTAINER = os.getenv("RIVERBEND_CONTAINER", "riverbend-app-1")
OUT_DIR = "/tmp/opencode/riverbend-rec"
VIDEO_SIZE = {"width": 1280, "height": 760}

DEFECT_CSV = """order_id,customer_id,order_ts,amount_cents,currency,status,updated_at
ord_2001,cus_08,2026-11-07T09:00:00Z,,USD,paid,2026-11-07T09:01:00Z
ord_2002,cus_09,2026-11-07T10:00:00Z,-100,USD,paid,2026-11-07T10:01:00Z
"""

FIX_CSV = """order_id,customer_id,order_ts,amount_cents,currency,status,updated_at
ord_2001,cus_08,2026-11-07T09:00:00Z,4500,USD,paid,2026-11-07T09:05:00Z
ord_2002,cus_09,2026-11-07T10:00:00Z,7800,USD,paid,2026-11-07T10:05:00Z
"""

CAPTION_JS = """
(text) => {
  let el = document.getElementById('demo-caption');
  if (!el) {
    el = document.createElement('div');
    el.id = 'demo-caption';
    el.style.cssText = [
      'position:fixed', 'left:50%', 'bottom:22px', 'transform:translateX(-50%)',
      'background:rgba(16,24,40,.92)', 'color:#fff', 'z-index:9999',
      'font:600 15px/1.45 Inter,system-ui,sans-serif', 'padding:10px 18px',
      'border-radius:10px', 'max-width:84%', 'text-align:center',
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


LOCAL = os.getenv("RIVERBEND_LOCAL") == "1"


def ssh(command: str) -> str:
    argv = ["bash", "-lc", command] if LOCAL else ["ssh", "-o", "StrictHostKeyChecking=no", HOST, command]
    result = subprocess.run(argv, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-300:])
    return result.stdout


def push_and_run(name: str, content: str) -> str:
    encoded = base64.b64encode(content.encode()).decode()
    ssh(
        f"echo {encoded} | base64 -d | docker exec -i {CONTAINER} sh -c 'cat > /app/data/incoming/{name}'"
    )
    code = (
        "from riverbend.pipeline import Pipeline; "
        f"p=Pipeline('/app/data/riverbend.duckdb'); "
        f"r=p.run_csv('/app/data/incoming/{name}'); "
        "print({'seen': r.rows_seen, 'valid': r.rows_valid, 'quarantined': r.rows_quarantined, 'upserted': r.rows_upserted}); "
        "p.close()"
    )
    out = ssh(f"docker exec {CONTAINER} python -c \"{code}\"")
    ssh(f"docker exec {CONTAINER} sh -c 'cd /app/dbt && dbt build --profiles-dir . >/dev/null 2>&1'")
    return out.strip()


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
    page.goto(URL, wait_until="commit", timeout=60000)
    page.get_by_text("Paid revenue").first.wait_for(timeout=30000)
    page.wait_for_timeout(1500)
    caption(page, "Personal demo project — fictional data", 2400)
    caption(page, "Initial load: 9 orders, $877.00 paid, 2 open quarantine rows", 3200)

    caption(page, "A defective file arrives with 2 invalid rows")
    defect = push_and_run("defect_2026_11_07.csv", DEFECT_CSV)
    print("defect:", defect)
    page.reload(wait_until="commit", timeout=60000)
    page.get_by_text("Paid revenue").first.wait_for(timeout=30000)
    page.wait_for_timeout(2500)
    caption(page, "Both rows quarantined; open quarantine goes to 4", 3400)

    caption(page, "The source is corrected and re-delivered")
    fix = push_and_run("fix_2026_11_07.csv", FIX_CSV)
    print("fix:", fix)
    page.reload(wait_until="commit", timeout=60000)
    page.get_by_text("Paid revenue").first.wait_for(timeout=30000)
    page.wait_for_timeout(2600)
    caption(page, "Orders 11, revenue $1,000.00, open quarantine back to 2", 3800)

    video = page.video
    context.close()
    browser.close()
    path = video.path()
    print(f"video: {path}")
    print(f"size: {os.path.getsize(path)} bytes")
