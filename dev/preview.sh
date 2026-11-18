#!/usr/bin/env bash
# Render every layout and state from dev/mock/*.json and screenshot them at 800x480.
#
#   PHP=/path/to/php LIQUID_SRC=/path/to/php-liquid/src OUT=/tmp/pkp-preview dev/preview.sh
#
# Needs: PHP 8.2+ (mbstring), keepsuit/php-liquid v0.12.1 sources, Chrome or Edge.
set -euo pipefail
cd "$(dirname "$0")/.."

PHP=${PHP:-php}
LIQUID_SRC=${LIQUID_SRC:?set LIQUID_SRC to keepsuit php-liquid/src}
OUT=${OUT:-dev/preview}
BROWSER=${BROWSER:-"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"}
mkdir -p "$OUT"

python dev/mock_data.py >/dev/null

render() { # name payload size lang station_id
  "$PHP" dev/render.php "$LIQUID_SRC" "dev/mock/$2.json" "$3" "$OUT/$1.html" "$4" "$5"
  local html
  html=$(cd "$OUT" && pwd -W 2>/dev/null || pwd)/$1.html
  "$BROWSER" --headless=new --disable-gpu --hide-scrollbars --window-size=800,480 \
    --virtual-time-budget=4000 --screenshot="$(dirname "$html")/$1.png" "file:///$html" 2>/dev/null
}

for size in full half_horizontal half_vertical quadrant; do
  render "board_$size" board "$size" pl 33019
done
render board_full_en board full en 33019
render lookup_full lookup full pl ""
render lookup_quadrant lookup quadrant en ""
render lookup_none lookup_empty full pl ""
render api_error api_error full pl 33019
render too_big too_big half_horizontal pl 33019
render empty_day empty_day full en 33019
echo "previews in $OUT"
