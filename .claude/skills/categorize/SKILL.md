---
name: categorize
description: Categorize generated outputs for a probe session along output axes
---

# Output Categorization

Executes Stage 3 of the pipeline (see docs/PIPELINE.md).

## Step 1: Identify Session

Ask the user which experiment, or find the most recent completed session:
```
GET /api/probes
```

## Step 2: Read Classification Rules

Find the probe guide from `sentence_set_name`:
```
glob data/sentence_sets/**/{sentence_set_name}.md
```

Read the **Output Axes** section — it contains classification rules for each axis and value.

Also read the sentence set JSON to get the `output_axes` array (axis IDs and valid values).

## Step 3: Read Generated Outputs

```
GET /api/probes/sessions/{session_id}/generated-outputs
```

Returns list of `{probe_id, input_text, label, generated_text, output_category}`.

**Skip** any probes that already have `output_category` set (resumability).

## Step 4: Classify Each Output

For each `generated_text`, determine:
- **Per-axis classification**: Read the text and assign a value for each output axis
- **Primary output_category**: The main classification label (may be a single axis value or a composite)

Use the probe guide's classification rules. When uncertain, use "ambiguous" or the closest match.

## Step 5: POST Categories

Build the batch payload and POST:
```
POST /api/probes/sessions/{session_id}/output-categories
{
  "probe_id_1": {
    "output_category": "value",
    "output_category_json": "{\"axis_id\": \"value\"}"
  }
}
```

**Important**: `output_category_json` must be a JSON **string**, not a dict.

Process in batches if needed (hundreds of probes).

## Step 6: Report

After posting, report:
- Total probes categorized
- Distribution per output_category value
- Any notable patterns (e.g., "78% of aquarium inputs produced aquarium continuations")
