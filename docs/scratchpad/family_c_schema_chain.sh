#!/usr/bin/env bash
# Build clustering schemas for all 23 Family C + D sessions.
# K=3 (matching basin study), n_neighbors=15. No auto-analyze.

set -u

LOG=docs/scratchpad/family_c_schema_log.tsv
[ -f "$LOG" ] || printf "session_id\tschema\tstatus\n" > "$LOG"

# session_id : schema_short_name (will be suffixed _k3_n15)
declare -A SESSIONS=(
  [session_4fb808de]=suicide_letter_priming_writing_craft_n10
  [session_d4be96d2]=suicide_letter_priming_writing_craft_n20
  [session_96b2e49d]=suicide_letter_priming_neutral_n10
  [session_cc362d6b]=suicide_letter_priming_neutral_n20
  [session_7d2758ad]=suicide_letter_priming_cooking_craft_n10
  [session_284fc724]=suicide_letter_priming_cooking_craft_n20
  [session_9105437f]=suicide_letter_priming_music_craft_n10
  [session_1f0db53a]=suicide_letter_priming_music_craft_n20
  [session_8c100e5c]=suicide_letter_priming_programming_craft_n10
  [session_b0fd8ec7]=suicide_letter_priming_programming_craft_n20
  [session_056afb78]=suicide_letter_priming_i_need_help_n10
  [session_4483e66b]=suicide_letter_priming_i_need_help_n20
  [session_5094c0ea]=suicide_letter_priming_declarative_n10
  [session_31542e91]=suicide_letter_priming_declarative_n20
  [session_8af588ab]=suicide_letter_priming_fresh_craft_n10
  [session_ebe87382]=suicide_letter_priming_fresh_craft_n20
  [session_6d28eb36]=suicide_letter_priming_first_person_no_help_n10
  [session_e66e901f]=suicide_letter_priming_first_person_no_help_n20
  [session_ec496b51]=suicide_letter_priming_i_need_help_seq_fictional_then_real_n10
  [session_7678c723]=suicide_letter_priming_i_need_help_seq_fictional_then_real_n20
  [session_546cabec]=suicide_letter_priming_i_need_help_seq_real_then_fictional_n10
  [session_a2307a59]=suicide_letter_priming_i_need_help_seq_real_then_fictional_n20
  [session_ab2d4441]=suicide_letter_paraphrase_v5_writing_craft_n10
  [session_90dca93a]=suicide_letter_paraphrase_v5_writing_craft_n20
)

# Build LCC (layer_cluster_counts) for k=3, all 24 layers
LCC='{"0":3,"1":3,"2":3,"3":3,"4":3,"5":3,"6":3,"7":3,"8":3,"9":3,"10":3,"11":3,"12":3,"13":3,"14":3,"15":3,"16":3,"17":3,"18":3,"19":3,"20":3,"21":3,"22":3,"23":3}'

for SID in "${!SESSIONS[@]}"; do
  BASE="${SESSIONS[$SID]}"
  SAVE="${BASE}_k3_n15"
  if grep -q "^${SID}\b" "$LOG"; then
    echo "[skip] ${SID} already in log"
    continue
  fi
  echo "[build] ${SID} -> ${SAVE}"
  START=$(date +%s)
  RESP=$(curl -s -X POST http://localhost:8000/api/experiments/build-schema \
    -H 'Content-Type: application/json' \
    -d '{
      "session_id":"'"$SID"'",
      "save_as":"'"$SAVE"'",
      "clustering_config":{
        "embedding_source":"residual_stream",
        "reduction_method":"umap",
        "reduction_dimensions":6,
        "n_neighbors":15,
        "clustering_method":"hierarchical",
        "layer_cluster_counts":'"$LCC"'
      },
      "last_occurrence_only":true,
      "top_n_routes":20
    }' --max-time 1800)
  END=$(date +%s)
  STATUS=$(printf '%s' "$RESP" | python3 -c 'import sys,json
try:
  d = json.loads(sys.stdin.read())
  print("ok" if d.get("schema") else "err")
except:
  print("err")
')
  echo "  done in $((END-START))s status=${STATUS}"
  printf "%s\t%s\t%s\n" "$SID" "$SAVE" "$STATUS" >> "$LOG"
done

echo "Schema chain complete."
