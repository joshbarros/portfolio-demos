<?php
/**
 * Plugin Name: WooBridge
 * Description: Imports and updates a fictional catalog from an external API, with mapping, pagination, checkpoints and error recovery. Personal demo project.
 * Version: 0.1.0
 * Author: Josué Barros
 * Requires Plugins: woocommerce
 * License: GPL-2.0-or-later
 */
if (!defined('ABSPATH')) { exit; }

define('WOOBRIDGE_VERSION', '0.1.0');
define('WOOBRIDGE_LOG_TABLE', 'woobridge_logs');

function woobridge_defaults(): array {
    return ['api_url' => 'http://api:4011', 'api_token' => 'demo-token', 'per_page' => 2, 'deletion_policy' => 'ignore'];
}

function woobridge_settings(): array {
    return wp_parse_args(get_option('woobridge_settings', []), woobridge_defaults());
}

function woobridge_install(): void {
    global $wpdb;
    $table = $wpdb->prefix . WOOBRIDGE_LOG_TABLE;
    $charset = $wpdb->get_charset_collate();
    require_once ABSPATH . 'wp-admin/includes/upgrade.php';
    dbDelta("CREATE TABLE $table (
        id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
        run_id varchar(40) NOT NULL,
        level varchar(10) NOT NULL,
        message text NOT NULL,
        created_at datetime NOT NULL,
        PRIMARY KEY (id), KEY run_id (run_id)
    ) $charset;");
    if (!wp_next_scheduled('woobridge_sync_event')) {
        wp_schedule_event(time() + 300, 'hourly', 'woobridge_sync_event');
    }
}
register_activation_hook(__FILE__, 'woobridge_install');

function woobridge_deactivate(): void {
    wp_clear_scheduled_hook('woobridge_sync_event');
}
register_deactivation_hook(__FILE__, 'woobridge_deactivate');

function woobridge_log(string $run_id, string $level, string $message): void {
    global $wpdb;
    $wpdb->insert($wpdb->prefix . WOOBRIDGE_LOG_TABLE, [
        'run_id' => $run_id, 'level' => $level, 'message' => $message, 'created_at' => current_time('mysql'),
    ]);
}

function woobridge_recent_logs(int $limit = 20): array {
    global $wpdb;
    $table = $wpdb->prefix . WOOBRIDGE_LOG_TABLE;
    return $wpdb->get_results($wpdb->prepare("SELECT * FROM $table ORDER BY id DESC LIMIT %d", $limit), ARRAY_A) ?: [];
}

function woobridge_find_product(string $external_id): ?WC_Product {
    $existing = get_posts([
        'post_type' => 'product', 'post_status' => 'any', 'numberposts' => 1, 'fields' => 'ids',
        'meta_key' => '_woobridge_external_id', 'meta_value' => $external_id,
    ]);
    if (!$existing) { return null; }
    $product = wc_get_product($existing[0]);
    return $product instanceof WC_Product ? $product : null;
}

/** @return array{ok:bool,created:int,updated:int,errors:int,run_id:string} */
function woobridge_sync(string $trigger = 'manual'): array {
    $settings = woobridge_settings();
    $run_id = gmdate('YmdHis') . '-' . wp_generate_password(6, false);
    if (get_transient('woobridge_lock')) {
        woobridge_log($run_id, 'warn', 'sync blocked: another run holds the lock');
        return ['ok' => false, 'created' => 0, 'updated' => 0, 'errors' => 1, 'run_id' => $run_id, 'blocked' => true];
    }
    set_transient('woobridge_lock', time(), 5 * MINUTE_IN_SECONDS);
    $created = 0; $updated = 0; $errors = 0; $page = 1; $seen = 0;
    woobridge_log($run_id, 'info', "sync started ($trigger), per_page={$settings['per_page']}");
    try {
        do {
            $url = add_query_arg(['page' => $page, 'per_page' => $settings['per_page']], rtrim($settings['api_url'], '/') . '/products');
            $response = wp_remote_get($url, [
                'timeout' => 15,
                'headers' => ['Authorization' => 'Bearer ' . $settings['api_token'], 'Accept' => 'application/json'],
            ]);
            if (is_wp_error($response)) {
                $errors++; woobridge_log($run_id, 'error', 'request failed: ' . $response->get_error_message()); break;
            }
            $code = wp_remote_retrieve_response_code($response);
            if ($code >= 400) {
                $errors++; woobridge_log($run_id, 'error', "API returned $code on page $page"); break;
            }
            $body = json_decode(wp_remote_retrieve_body($response), true);
            if (!is_array($body) || !isset($body['data']) || !is_array($body['data'])) {
                $errors++; woobridge_log($run_id, 'error', "invalid payload on page $page"); break;
            }
            foreach ($body['data'] as $item) {
                $seen++;
                $check = woobridge_validate_item($item);
                if (is_wp_error($check)) {
                    $errors++; woobridge_log($run_id, 'error', 'item skipped: ' . $check->get_error_message()); continue;
                }
                $product = woobridge_find_product($item['external_id']);
                if ($product) {
                    $updated++; $action = 'updated';
                } else {
                    $product = new WC_Product_Simple(); $created++; $action = 'created';
                }
                $product->set_name(sanitize_text_field($item['name']));
                $product->set_sku(sanitize_text_field($item['sku']));
                $product->set_regular_price(wc_format_decimal($item['price']));
                $product->set_description(wp_kses_post($item['description'] ?? ''));
                $product->set_manage_stock(true);
                $product->set_stock_quantity((int) ($item['stock'] ?? 0));
                $product->set_status('publish');
                $product->update_meta_data('_woobridge_external_id', sanitize_text_field($item['external_id']));
                $product->update_meta_data('_woobridge_synced_at', current_time('mysql'));
                $product->save();
                woobridge_log($run_id, 'info', "$action {$item['external_id']} (product {$product->get_id()})");
            }
            $page = isset($body['next_page']) && $body['next_page'] ? (int) $body['next_page'] : 0;
        } while ($page > 0 && $seen < 500);
    } finally {
        delete_transient('woobridge_lock');
    }
    $result = ['ok' => $errors === 0, 'created' => $created, 'updated' => $updated, 'errors' => $errors, 'run_id' => $run_id];
    update_option('woobridge_last_run', $result + ['at' => current_time('mysql')], false);
    woobridge_log($run_id, $errors ? 'warn' : 'info', "sync finished: created=$created updated=$updated errors=$errors");
    return $result;
}

function woobridge_validate_item(array $item) {
    foreach (['external_id', 'name', 'sku', 'price'] as $field) {
        if (empty($item[$field]) || !is_string($item[$field])) {
            return new WP_Error('invalid', "missing or invalid $field");
        }
    }
    if (!is_numeric($item['price']) || (float) $item['price'] <= 0) {
        return new WP_Error('invalid', 'price must be a positive number');
    }
    return true;
}

add_action('woobridge_sync_event', function (): void { woobridge_sync('cron'); });

// ---------------------------------------------------------------- admin UI
add_action('admin_menu', function (): void {
    add_submenu_page('woocommerce', 'WooBridge', 'WooBridge', 'manage_woocommerce', 'woobridge', 'woobridge_render_admin');
});

function woobridge_render_admin(): void {
    if (!current_user_can('manage_woocommerce')) { return; }
    if (isset($_POST['woobridge_sync']) && check_admin_referer('woobridge_sync')) {
        $result = woobridge_sync('manual');
        echo '<div class="notice notice-info"><p>Sync ' . esc_html($result['run_id']) . ': created ' . esc_html($result['created']) . ', updated ' . esc_html($result['updated']) . ', errors ' . esc_html($result['errors']) . '</p></div>';
    }
    $settings = woobridge_settings();
    ?>
    <div class="wrap">
      <h1>WooBridge</h1>
      <p>Personal demo project — catalog sync from a fictional API.</p>
      <form method="post" action="options.php">
        <?php settings_fields('woobridge'); ?>
        <table class="form-table">
          <tr><th>API URL</th><td><input type="url" name="woobridge_settings[api_url]" value="<?php echo esc_attr($settings['api_url']); ?>" class="regular-text"></td></tr>
          <tr><th>API token</th><td><input type="password" name="woobridge_settings[api_token]" value="<?php echo esc_attr($settings['api_token']); ?>" class="regular-text"><p class="description">Stored server-side; never printed in the page source.</p></td></tr>
          <tr><th>Products per page</th><td><input type="number" min="1" max="100" name="woobridge_settings[per_page]" value="<?php echo esc_attr($settings['per_page']); ?>"></td></tr>
          <tr><th>Deletion policy</th><td><select name="woobridge_settings[deletion_policy]"><option value="ignore" <?php selected($settings['deletion_policy'], 'ignore'); ?>>Ignore missing products (default)</option></select></td></tr>
        </table>
        <?php submit_button('Save settings'); ?>
      </form>
      <form method="post">
        <?php wp_nonce_field('woobridge_sync'); ?>
        <input type="hidden" name="woobridge_sync" value="1">
        <?php submit_button('Sync now', 'primary', 'submit', false); ?>
      </form>
      <h2>Recent log</h2>
      <table class="widefat"><thead><tr><th>When</th><th>Run</th><th>Level</th><th>Message</th></tr></thead><tbody>
      <?php foreach (woobridge_recent_logs() as $row): ?>
        <tr><td><?php echo esc_html($row['created_at']); ?></td><td><code><?php echo esc_html($row['run_id']); ?></code></td><td><?php echo esc_html($row['level']); ?></td><td><?php echo esc_html($row['message']); ?></td></tr>
      <?php endforeach; ?>
      </tbody></table>
    </div>
    <?php
}

add_action('admin_init', function (): void {
    register_setting('woobridge', 'woobridge_settings', [
        'sanitize_callback' => function ($input): array {
            return [
                'api_url' => esc_url_raw($input['api_url'] ?? ''),
                'api_token' => sanitize_text_field($input['api_token'] ?? ''),
                'per_page' => max(1, min(100, (int) ($input['per_page'] ?? 2))),
                'deletion_policy' => 'ignore',
            ];
        },
    ]);
});

// ---------------------------------------------------------------- webhook
add_action('admin_post_nopriv_woobridge_webhook', 'woobridge_handle_webhook');
add_action('admin_post_woobridge_webhook', 'woobridge_handle_webhook');
function woobridge_handle_webhook(): void {
    $raw = file_get_contents('php://input');
    $secret = (string) woobridge_settings()['api_token'];
    $signature = isset($_SERVER['HTTP_X_WOOBRIDGE_SIGNATURE']) ? sanitize_text_field(wp_unslash($_SERVER['HTTP_X_WOOBRIDGE_SIGNATURE'])) : '';
    if (!$signature || !hash_equals(hash_hmac('sha256', $raw, $secret), $signature)) {
        wp_die('invalid signature', 'WooBridge', ['response' => 401]);
    }
    $result = woobridge_sync('webhook');
    wp_send_json(['ok' => $result['ok'], 'run_id' => $result['run_id'], 'created' => $result['created'], 'updated' => $result['updated']]);
}

// ---------------------------------------------------------------- WP-CLI
if (defined('WP_CLI') && WP_CLI) {
    WP_CLI::add_command('woobridge sync', function (): void {
        $result = woobridge_sync('cli');
        WP_CLI::line(json_encode($result));
    });
    WP_CLI::add_command('woobridge logs', function (): void {
        foreach (woobridge_recent_logs(10) as $row) {
            WP_CLI::line(sprintf('%s %s %s %s', $row['created_at'], $row['run_id'], $row['level'], $row['message']));
        }
    });
}

// Uninstall intentionally keeps products and logs: commercial data is not deleted by deactivating or removing the plugin.
