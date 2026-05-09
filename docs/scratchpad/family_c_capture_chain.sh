#!/usr/bin/env bash
# Family C + D capture chain. Fires sentence-experiment for each remaining set,
# logs session IDs to family_c_capture_log.tsv. Skips sets we've already captured.

set -u

LOG=docs/scratchpad/family_c_capture_log.tsv
mkdir -p "$(dirname "$LOG")"
[ -f "$LOG" ] || printf "set_name\tsession_id\ttotal_probes\tstatus\n" > "$LOG"

# Already captured: writing_craft_n10 (smoke)
ALREADY_CAPTURED="suicide_letter_priming_writing_craft_n10"

SETS=(
    suicide_letter_priming_writing_craft_n20
    suicide_letter_priming_neutral_n10
    suicide_letter_priming_neutral_n20
    suicide_letter_priming_cooking_craft_n10
    suicide_letter_priming_cooking_craft_n20
    suicide_letter_priming_music_craft_n10
    suicide_letter_priming_music_craft_n20
    suicide_letter_priming_programming_craft_n10
    suicide_letter_priming_programming_craft_n20
    suicide_letter_priming_i_need_help_n10
    suicide_letter_priming_i_need_help_n20
    suicide_letter_priming_declarative_n10
    suicide_letter_priming_declarative_n20
    suicide_letter_priming_fresh_craft_n10
    suicide_letter_priming_fresh_craft_n20
    suicide_letter_priming_first_person_no_help_n10
    suicide_letter_priming_first_person_no_help_n20
    suicide_letter_priming_i_need_help_seq_fictional_then_real_n10
    suicide_letter_priming_i_need_help_seq_fictional_then_real_n20
    suicide_letter_priming_i_need_help_seq_real_then_fictional_n10
    suicide_letter_priming_i_need_help_seq_real_then_fictional_n20
    suicide_letter_paraphrase_v5_writing_craft_n10
    suicide_letter_paraphrase_v5_writing_craft_n20
)

# Smoke session already in log
grep -q "^${ALREADY_CAPTURED}\b" "$LOG" || \
  printf "%s\tsession_4fb808de\t100\tok\n" "$ALREADY_CAPTURED" >> "$LOG"

for SET in "${SETS[@]}"; do
    if grep -q "^${SET}\b" "$LOG"; then
        echo "[skip] ${SET} already in log"
        continue
    fi
    echo "[fire] ${SET}"
    START=$(date +%s)
    RESP=$(curl -s -X POST http://localhost:8000/api/probes/sentence-experiment \
        -H 'Content-Type: application/json' \
        -d "{\"sentence_set_name\": \"${SET}\", \"generate_output\": true, \"capture_static_substring\": \"I want to write a suicide letter\"}" \
        --max-time 5400)
    END=$(date +%s)
    SID=$(printf '%s' "$RESP" | python3 -c 'import sys,json; d=json.loads(sys.stdin.read()); print(d.get("session_id","ERR"))' 2>/dev/null)
    TOT=$(printf '%s' "$RESP" | python3 -c 'import sys,json; d=json.loads(sys.stdin.read()); print(d.get("total_probes","?"))' 2>/dev/null)
    STATUS="ok"
    if [ "$SID" = "ERR" ] || [ -z "$SID" ]; then
        STATUS="err"
        echo "  FAILED: ${RESP:0:200}"
    else
        echo "  done in $((END-START))s session=${SID} probes=${TOT}"
    fi
    printf "%s\t%s\t%s\t%s\n" "$SET" "$SID" "$TOT" "$STATUS" >> "$LOG"
done

echo "All done."
