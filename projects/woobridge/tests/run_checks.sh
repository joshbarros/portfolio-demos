#!/usr/bin/env bash
# End-to-end checks for the WooBridge demo. Requires the compose stack running.
set -uo pipefail
cd "$(dirname "$0")/.."
WP="docker compose exec -T wpcli wp"
pass=0; fail=0
ok() { echo "PASS $1"; pass=$((pass+1)); }
bad() { echo "FAIL $1"; fail=$((fail+1)); }

count_products() { $WP post list --post_type=product --format=count 2>/dev/null | tr -d '\r'; }
sync() { $WP woobridge sync 2>/dev/null | tail -1; }
price_of() { $WP eval 'echo wc_get_product(wc_get_product_id_by_sku("HL-1001"))->get_regular_price();' 2>/dev/null; }
control() { curl -s -X POST http://127.0.0.1:4011/_control -H 'content-type: application/json' -d "$1" >/dev/null; }

$WP plugin is-active woobridge >/dev/null 2>&1 && ok "plugin active" || bad "plugin active"

before=$(count_products)
if [ "$before" -ge 3 ]; then ok "first import created products ($before)"; else bad "first import ($before)"; fi

out=$(sync)
if echo "$out" | grep -q '"created":0' && echo "$out" | grep -q '"updated":3'; then ok "re-run updates without duplicating"; else bad "re-run: $out"; fi
after=$(count_products)
[ "$after" -eq "$before" ] && ok "product count unchanged ($after)" || bad "duplicated products ($before -> $after)"

control '{"update":{"external_id":"ext_1001","price":"59.90"}}'
sync >/dev/null
[ "$(price_of)" = "59.90" ] && ok "price updated from source" || bad "price update ($(price_of))"

control '{"invalid":true}'
out=$(sync)
echo "$out" | grep -q '"errors":[1-9]' && ok "invalid payload reported as error" || bad "invalid payload not reported: $out"
control '{"invalid":false}'

control '{"fail":true}'
out=$(sync)
echo "$out" | grep -q '"errors":[1-9]' && ok "temporary API failure reported" || bad "failure not reported: $out"
control '{"fail":false}'
out=$(sync)
echo "$out" | grep -q '"ok":true' && ok "recovery after failure" || bad "recovery failed: $out"

$WP eval 'set_transient("woobridge_lock", time(), 300);' >/dev/null 2>&1
out=$(sync)
echo "$out" | grep -q '"blocked":true' && ok "concurrent sync blocked by lock" || bad "lock not enforced: $out"
$WP eval 'delete_transient("woobridge_lock");' >/dev/null 2>&1

out=$($WP woobridge logs 2>/dev/null | grep -c 'ext_1003\|TC-1003')
[ "$out" -ge 1 ] && ok "pagination reached the second page" || bad "pagination evidence missing"

code=$(curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:8080/wp-admin/admin-post.php?action=woobridge_webhook -H 'content-type: application/json' -d '{}')
[ "$code" = "401" ] && ok "webhook rejects unsigned payload" || bad "webhook signature ($code)"

echo "---"
echo "passed=$pass failed=$fail"
[ "$fail" -eq 0 ]
