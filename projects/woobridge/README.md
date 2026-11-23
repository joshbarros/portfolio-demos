# WooBridge

**Custom WooCommerce API Sync Plugin with Mapping and Error Recovery**

Personal demo project. An installable WordPress plugin imports and updates a fictional catalog from an
external API, with pagination, stable external ids, a run log, a concurrency lock and recovery.

> The demo runs **locally only**. A full wp-admin with administrator rights is not exposed publicly;
> the evidence is the recorded flow and the scripts below.

## Flow

1. Settings: API URL, token (stored server-side, masked), page size, deletion policy.
2. Sync now (or hourly WP-Cron, or an authenticated webhook) fetches the API page by page.
3. Each product is validated and upserted by the `_woobridge_external_id` product meta.
4. Existing products are updated, never duplicated. Missing products are ignored by default.
5. Every run is logged with created/updated/errors and per-item messages.
6. A transient lock blocks concurrent syncs.

## Endpoints

- Manual: WooCommerce → WooBridge → **Sync now** (nonce + `manage_woocommerce`).
- Scheduled: `woobridge_sync_event` (hourly, WP-Cron; depends on site traffic unless a real cron is configured).
- Webhook: `POST /wp-admin/admin-post.php?action=woobridge_webhook` with `X-Woobridge-Signature` = HMAC-SHA256 of the raw body using the API token. Unsigned requests get 401.
- WP-CLI: `wp woobridge sync`, `wp woobridge logs`.

## Tests

`tests/run_checks.sh` (11 checks, all passing): plugin active, first import, re-run without
duplication, price update from source, invalid payload reported, temporary API failure, recovery,
concurrent sync blocked, pagination to page 2, unsigned webhook rejected.

## Run locally

```bash
docker compose up -d
# wait for WordPress, then:
docker compose exec -T wpcli wp core install --url=http://127.0.0.1:8080 --title="WooBridge Demo" --admin_user=admin --admin_password=demo --admin_email=demo@example.com --skip-email
docker compose exec -T wpcli wp plugin install woocommerce --version=9.5.1 --activate
docker compose exec -T wpcli wp plugin activate woobridge
./tests/run_checks.sh
```

Open http://127.0.0.1:8080/wp-admin (admin / demo) → WooCommerce → WooBridge.

## Deletion policy and uninstall

- Missing products are **ignored**, not deleted. The policy is explicit in the settings screen and in
  code; only the `ignore` option exists in this demo.
- Deactivating or uninstalling the plugin **keeps** products and logs. Commercial data is not deleted
  by plugin removal.

## Limitations

- WP-Cron runs on traffic; exact hourly execution is not guaranteed without a system cron.
- The demo uses a fictional API and products; no real store or customer data.
- Product variations, images, categories and attributes are out of scope.
- The plugin targets simple products and the WooCommerce 9.5 API.
