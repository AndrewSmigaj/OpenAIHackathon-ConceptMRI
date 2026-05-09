#!/usr/bin/env bash
# Tank polysemy paper-protocol capture chain (20 sets × 40 probes = 800 probes).
# To close F12 (polysemy methodology validation) to Robust.

set -u

LOG=docs/scratchpad/polysemy_capture_log.tsv
[ -f "$LOG" ] || printf "set_name\tsession_id\ttotal_probes\tstatus\n" > "$LOG"

SETS=()
for direction in aquarium_then_vehicle vehicle_then_aquarium; do
  for ord in 0 1 2 3 4 5 6 7 8 9; do
    SETS+=("tank_polysemy_paper_protocol_${direction}_ord${ord}")
  done
done

for SET in "${SETS[@]}"; do
    if grep -q "^${SET}\b" "$LOG"; then
        echo "[skip] ${SET} already in log"
        continue
    fi
    echo "[fire] ${SET}"
    START=$(date +%s)
    # No multi-token capture needed for polysemy — basin projection works at target token directly
    RESP=$(curl -s -X POST http://localhost:8000/api/probes/sentence-experiment \
        -H 'Content-Type: application/json' \
        -d "{\"sentence_set_name\": \"${SET}\", \"generate_output\": false}" \
        --max-time 5400)
    END=$(date +%s)
    SID=$(printf '%s' "$RESP" | python3 -c 'import sys,json
try:
  d = json.loads(sys.stdin.read())
  print(d.get("session_id","ERR"))
except:
  print("ERR")')
    TOT=$(printf '%s' "$RESP" | python3 -c 'import sys,json
try:
  d = json.loads(sys.stdin.read())
  print(d.get("total_probes","?"))
except:
  print("?")')
    STATUS="ok"
    if [ "$SID" = "ERR" ] || [ -z "$SID" ]; then
        STATUS="err"
        echo "  FAILED (curl timeout? server may still be processing)"
    else
        echo "  done in $((END-START))s session=${SID} probes=${TOT}"
    fi
    printf "%s\t%s\t%s\t%s\n" "$SET" "$SID" "$TOT" "$STATUS" >> "$LOG"
done

echo "Polysemy chain complete."
