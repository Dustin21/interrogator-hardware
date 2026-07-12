#!/usr/bin/env bash
# Round 3 — the three stragglers found during VERIFY closure round 2:
#   BL54L15  : round-1/2 file was a saved HTML page, not a PDF (Ezurio landing page).
#              Real asset: EZ-DS-BL54L15_v1_9.pdf (v1.9, Jun 2025, covers BL54L10+L15).
#   SGX-4CO  : round-1 file was 0 bytes AND the doc ID was wrong — DS-0143 is the
#              SGX-4OX (oxygen) sheet. Correct CO doc: DS-0138 v3.
#   LMP91000 : never fetched (potentiostat AFE for the SGX-4CO cell).
# Every download is validated: must start with %PDF and be >10 KB, else deleted+FAIL.
# Run from anywhere on the Mac:  bash fetch_datasheets_round3.sh
set -u
REG="${REG:-$HOME/Development/registry_assets}"
CURL=(curl -fSL --http1.1 --connect-timeout 8 --max-time 90
      -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")

ok=0; bad=0
fetch() { # fetch <PART> <filename> <url>
  local part="$1" name="$2" url="$3" dst="$REG/$1/datasheet/$2"
  mkdir -p "$(dirname "$dst")"
  if "${CURL[@]}" -o "$dst" "$url" \
     && [ "$(head -c4 "$dst" 2>/dev/null)" = "%PDF" ] \
     && [ "$(stat -f%z "$dst" 2>/dev/null || stat -c%s "$dst")" -gt 10240 ]; then
    echo "OK   $part/$name ($(du -h "$dst" | cut -f1 | tr -d ' '))"; ok=$((ok+1))
  else
    rm -f "$dst"; echo "FAIL $part/$name  <- $url"; bad=$((bad+1))
  fi
}

# stale/broken artifacts from earlier rounds
rm -f "$REG/SGX-4CO/datasheet/SGX-4CO-Datasheet.pdf"          # 0 bytes
rm -f "$REG/BL54L15/datasheet/BL54L15_DS.pdf"                 # HTML, not PDF

fetch BL54L15  EZ-DS-BL54L15_v1_9.pdf \
  "https://connectivity-staging.s3.us-east-2.amazonaws.com/2025-06/EZ-DS-BL54L15_v1_9.pdf"
fetch SGX-4CO  DS-0138-SGX-4CO-datasheet-v3.pdf \
  "https://www.sgxsensortech.com/content/uploads/2014/07/DS-0138-SGX-4CO-datasheet-v3.pdf"
fetch LMP91000 lmp91000.pdf \
  "https://www.ti.com/lit/ds/symlink/lmp91000.pdf"

echo "----"; echo "round 3: $ok ok, $bad failed"
[ $bad -gt 0 ] && cat <<'EOF'
Browser fallback for any FAIL above: open the URL, save the PDF into
~/Development/registry_assets/<PART>/datasheet/ with the same filename.
EOF
exit 0
