#!/usr/bin/env bash
# Polysemy paper-protocol via /api/experiments/temporal-capture
# with processing_mode=expanding_cache_on. 10 orderings x 2 directions = 20 runs.

set -u

LOG=docs/scratchpad/polysemy_temporal_log.tsv
[ -f "$LOG" ] || printf "ord\tdir\tsequence_config\trun_id\tnew_session\tprobes\tregime_boundary\tstatus\n" > "$LOG"

# Polysemy basin study + schema
SOURCE_SID=session_1434a9be
SCHEMA=tank_polysemy_k6_n15
BASIN_LAYER=23
# Pure clusters per basin findings: vehicle=4 (98% pure), aquarium=5 (92% pure)
A_CLUSTER=5  # aquarium
B_CLUSTER=4  # vehicle

# 10 orderings x 2 directions
for ord in 0 1 2 3 4 5 6 7 8 9; do
  for dir in block_ab block_ba; do
    LABEL="ord${ord}_${dir}"
    if grep -q "${LABEL}" "$LOG"; then
      echo "[skip] ${LABEL}"
      continue
    fi
    echo "[fire] ${LABEL}"
    START=$(date +%s)
    RESP=$(curl -s -X POST http://localhost:8000/api/experiments/temporal-capture \
      -H 'Content-Type: application/json' \
      -d "{
        \"session_id\": \"${SOURCE_SID}\",
        \"clustering_schema\": \"${SCHEMA}\",
        \"basin_layer\": ${BASIN_LAYER},
        \"basin_a_cluster_id\": ${A_CLUSTER},
        \"basin_b_cluster_id\": ${B_CLUSTER},
        \"sentences_per_block\": 20,
        \"processing_mode\": \"expanding_cache_on\",
        \"sequence_config\": \"${dir}\",
        \"generate_output\": false,
        \"run_label\": \"polysemy_paper_${LABEL}\"
      }" --max-time 1800)
    END=$(date +%s)
    RUN_ID=$(printf '%s' "$RESP" | python3 -c 'import sys,json
try: d=json.loads(sys.stdin.read()); print(d.get("temporal_run_id","ERR"))
except: print("ERR")')
    NEW_SID=$(printf '%s' "$RESP" | python3 -c 'import sys,json
try: d=json.loads(sys.stdin.read()); print(d.get("new_session_id","ERR"))
except: print("ERR")')
    PROBES=$(printf '%s' "$RESP" | python3 -c 'import sys,json
try: d=json.loads(sys.stdin.read()); print(d.get("sequence_positions","?"))
except: print("?")')
    REGIME=$(printf '%s' "$RESP" | python3 -c 'import sys,json
try: d=json.loads(sys.stdin.read()); print(d.get("regime_boundary","?"))
except: print("?")')
    STATUS="ok"
    if [ "$RUN_ID" = "ERR" ] || [ -z "$RUN_ID" ]; then
      STATUS="err"
      echo "  FAILED: ${RESP:0:200}"
    else
      echo "  done in $((END-START))s run=${RUN_ID} session=${NEW_SID} probes=${PROBES} regime=${REGIME}"
    fi
    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$ord" "$dir" "$dir" "$RUN_ID" "$NEW_SID" "$PROBES" "$REGIME" "$STATUS" >> "$LOG"
  done
done

echo "Polysemy temporal chain complete."
