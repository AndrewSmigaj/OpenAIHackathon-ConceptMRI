#!/usr/bin/env bash
# Suicide letter paper protocol WITH generate_output=true.
# 19 sessions (10 orderings x 2 directions = 20, minus smoke ord0_ba which already ran).
# Each session ~36 min wall-clock with gen-256. Total ~11.5 hours.

set -u

LOG=docs/scratchpad/paper_protocol_with_gen_log.tsv
[ -f "$LOG" ] || printf "ord\tdir\trun_id\tnew_session\tprobes\tregime_boundary\tstatus\n" > "$LOG"

# Smoke session_0f52c7b0 = suicide ord0_ba — record it
grep -q "^0	block_ba	" "$LOG" || \
  printf "0\tblock_ba\ttemporal_smoke_with_gen_001\tsession_0f52c7b0\t40\t20\tok_smoke\n" >> "$LOG"

fire() {
    local ORD=$1
    local DIR=$2
    if grep -q "^${ORD}	${DIR}	" "$LOG"; then
        echo "[skip] ord${ORD}_${DIR}"
        return
    fi
    echo "[fire] ord${ORD}_${DIR} ($(date '+%H:%M:%S'))"
    local START=$(date +%s)
    local RESP=$(curl -s -X POST http://localhost:8000/api/experiments/temporal-capture \
        -H 'Content-Type: application/json' \
        -d "{
            \"session_id\": \"session_9358c2a1\",
            \"clustering_schema\": \"suicide_letter_basin_k3_n15\",
            \"basin_layer\": 23,
            \"basin_a_cluster_id\": 1,
            \"basin_b_cluster_id\": 0,
            \"sentences_per_block\": 20,
            \"sequence_config\": \"${DIR}\",
            \"generate_output\": true,
            \"run_label\": \"paper_gen_suicide_ord${ORD}_${DIR}\"
        }" --max-time 3600)
    local END=$(date +%s)
    local RUN_ID=$(printf '%s' "$RESP" | python3 -c 'import sys,json
try: d=json.loads(sys.stdin.read()); print(d.get("temporal_run_id","ERR"))
except: print("ERR")')
    local NEW_SID=$(printf '%s' "$RESP" | python3 -c 'import sys,json
try: d=json.loads(sys.stdin.read()); print(d.get("new_session_id","ERR"))
except: print("ERR")')
    local PROBES=$(printf '%s' "$RESP" | python3 -c 'import sys,json
try: d=json.loads(sys.stdin.read()); print(d.get("sequence_positions","?"))
except: print("?")')
    local REGIME=$(printf '%s' "$RESP" | python3 -c 'import sys,json
try: d=json.loads(sys.stdin.read()); print(d.get("regime_boundary","?"))
except: print("?")')
    local STATUS="ok"
    if [ "$RUN_ID" = "ERR" ] || [ -z "$RUN_ID" ]; then
        STATUS="err"
        echo "  FAILED: ${RESP:0:200}"
    else
        echo "  done in $((END-START))s ($((END-START))/60 min) run=${RUN_ID} session=${NEW_SID}"
    fi
    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$ORD" "$DIR" "$RUN_ID" "$NEW_SID" "$PROBES" "$REGIME" "$STATUS" >> "$LOG"
}

# Order: alternate directions for variety in case we abort early
for ord in 0 1 2 3 4 5 6 7 8 9; do
    if [ "$ord" != "0" ]; then
        fire "$ord" block_ba
    fi
    fire "$ord" block_ab
done

echo "Suicide-letter paper protocol with generation complete: $(date '+%H:%M:%S')"
