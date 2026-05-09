#!/usr/bin/env bash
# Paper-protocol captures via the new unified harmony+cache-on path.
# 10 orderings x 2 directions per probe family. Cache-on means each
# ordering completes in seconds, not minutes.

set -u

LOG=docs/scratchpad/paper_protocol_log.tsv
[ -f "$LOG" ] || printf "family\tord\tdir\trun_id\tnew_session\tprobes\tregime_boundary\tstatus\n" > "$LOG"

fire_one() {
    local FAMILY=$1
    local SOURCE_SID=$2
    local SCHEMA=$3
    local A_CLUSTER=$4
    local B_CLUSTER=$5
    local ORD=$6
    local DIR=$7

    local LABEL="${FAMILY}_ord${ORD}_${DIR}"
    if grep -q "^${FAMILY}	${ORD}	${DIR}	" "$LOG"; then
        echo "[skip] ${LABEL}"
        return
    fi
    echo "[fire] ${LABEL}"
    local START=$(date +%s)
    local RESP=$(curl -s -X POST http://localhost:8000/api/experiments/temporal-capture \
        -H 'Content-Type: application/json' \
        -d "{
            \"session_id\": \"${SOURCE_SID}\",
            \"clustering_schema\": \"${SCHEMA}\",
            \"basin_layer\": 23,
            \"basin_a_cluster_id\": ${A_CLUSTER},
            \"basin_b_cluster_id\": ${B_CLUSTER},
            \"sentences_per_block\": 20,
            \"sequence_config\": \"${DIR}\",
            \"generate_output\": false,
            \"run_label\": \"paper_${FAMILY}_ord${ORD}_${DIR}\"
        }" --max-time 1200)
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
        echo "  done in $((END-START))s run=${RUN_ID} session=${NEW_SID} probes=${PROBES}"
    fi
    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
        "$FAMILY" "$ORD" "$DIR" "$RUN_ID" "$NEW_SID" "$PROBES" "$REGIME" "$STATUS" >> "$LOG"
}

# Polysemy: 10 orderings x 2 directions
for ord in 0 1 2 3 4 5 6 7 8 9; do
    for dir in block_ab block_ba; do
        fire_one polysemy session_1434a9be tank_polysemy_k6_n15 5 4 "$ord" "$dir"
    done
done

# Suicide letter: 10 orderings x 2 directions
for ord in 0 1 2 3 4 5 6 7 8 9; do
    for dir in block_ab block_ba; do
        fire_one suicide session_9358c2a1 suicide_letter_basin_k3_n15 1 0 "$ord" "$dir"
    done
done

echo "Paper protocol chain complete."
