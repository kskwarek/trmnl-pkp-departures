<?php

/**
 * Render the plugin the way Larapaper does (keepsuit/liquid, shared.liquid prepended,
 * `view view--{size}` wrapper, same context keys), and write a standalone HTML preview.
 *
 *   php dev/render.php <keepsuit-liquid/src> <payload.json> <size> <out.html> [lang] [station_id] [now_utc]
 *
 * keepsuit-liquid: git clone https://github.com/keepsuit/php-liquid && git checkout v0.12.1
 * (the version Larapaper pins). Only PHP 8.2+ with mbstring is needed, no Composer.
 */

[$_, $liquidSrc, $payloadPath, $size, $outPath] = $argv;
$lang = $argv[5] ?? 'pl';
$stationId = $argv[6] ?? '33019';
$nowUtc = (int) ($argv[7] ?? strtotime('2026-10-18T15:20:00Z'));

spl_autoload_register(function (string $class) use ($liquidSrc): void {
    $prefix = 'Keepsuit\\Liquid\\';
    if (str_starts_with($class, $prefix)) {
        $file = $liquidSrc.'/'.str_replace('\\', '/', substr($class, strlen($prefix))).'.php';
        if (is_file($file)) {
            require $file;
        }
    }
});

$pluginDir = dirname(__DIR__).'/src';
$payload = json_decode(file_get_contents($payloadPath), true, flags: JSON_THROW_ON_ERROR);

$config = [
    'api_key' => 'sk_live_dummy',
    'station_id' => $stationId,
    'station_search' => $stationId === '' ? 'Kraków' : '',
    'station_label' => '',
    'carriers' => '',
    'language' => $lang,
];

$context = [
    'size' => $size,
    'data' => $payload,
    'config' => $config,
    ...$payload,
    'trmnl' => [
        'system' => ['timestamp_utc' => $nowUtc],
        'user' => ['utc_offset' => '7200', 'time_zone_iana' => 'Europe/Warsaw', 'locale' => 'en', 'name' => 'Dev'],
        'plugin_settings' => [
            'instance_name' => 'PKP Departures',
            'custom_fields_values' => $config,
            'data_fetched_utc' => $nowUtc - 60,
        ],
    ],
];

// Same preprocessing as Plugin::applyLiquidReplacements().
function larapaperReplacements(string $template): string
{
    $template = preg_replace_callback(
        '/{%\s*for\s+(\w+)\s+in\s+([^|%}]+)\s*\|\s*([^%}]+)%}/',
        fn (array $m): string => "{% assign _tmp = {$m[2]} | {$m[3]} %}{% for {$m[1]} in _tmp %}",
        $template
    );

    return $template;
}

$layout = file_get_contents("$pluginDir/$size.liquid");
// PluginImportService::ensureLiquidViewWrapper()
$layout = '<div class="view view--{{ size }}">'."\n".$layout."\n".'</div>';
$markup = file_get_contents("$pluginDir/shared.liquid")."\n".$layout;

$env = new \Keepsuit\Liquid\Environment(extensions: [new \Keepsuit\Liquid\Extensions\StandardExtension()]);
$template = $env->parseString(larapaperReplacements($markup));
$started = microtime(true);
$html = $template->render($env->newRenderContext(data: $context));
$ms = round((microtime(true) - $started) * 1000);

$mashup = ['full' => null, 'half_horizontal' => '1Tx1B', 'half_vertical' => '1Lx1R', 'quadrant' => '2x2'][$size];
$body = $mashup ? "<div class=\"mashup mashup--$mashup\">$html</div>" : $html;

$page = <<<HTML
<!DOCTYPE html>
<html><head><meta charset="utf-8">
<base href="https://trmnl.com/">
<link rel="stylesheet" href="https://trmnl.com/css/3.4.0/plugins.css">
<script src="https://trmnl.com/js/3.4.0/plugins.js"></script>
<style>body{margin:0}</style>
</head><body class="environment trmnl">
<div class="screen screen--og screen--1bit screen--fonts-trmnl">$body</div>
</body></html>
HTML;

file_put_contents($outPath, $page);
fwrite(STDERR, "rendered $size in {$ms} ms -> $outPath\n");
