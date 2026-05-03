# CPA Experiment Notes - Point 768

## Experiment intent
Evaluate CPA effectiveness at the already selected optimal probe location, without moving the XYZ stage.

## Decisions locked for this run
- Scan point used: `768` (reference point from prior XY scan, originally `768.trs`).
- Stage movement during dedicated capture: **none**.
- Capture type: dedicated CPA set (not TVLA interleaving).
- Plaintext policy during dedicated capture: **random plaintexts**.
- Key policy: **fixed key for the whole run**, used for validation.
  - If `--key-hex` is omitted, the script generates a random 16-byte key and keeps it fixed for the run.
  - The key is printed and saved in capture metadata.
- Trace count target: `5000`.
- Output path policy: **do not change configured path**.
- Effectiveness metric requested: **aggregate rank curve vs number of traces**.
- Window selection policy: operator inspects traces and manually chooses a 1-2 AES-round window.

## Branch + repository state
- Working branch for this experiment: `cpa-point-768`.
- Prior local change in `xyz-stage/octoprint_communication.py` was intentionally discarded before starting this branch workflow.

## Scripts added for this workflow
- Dedicated no-move capture:
  - `xyz-stage/capture_cpa_current_position.py`
- CPA aggregate rank-curve analysis:
  - `sca-helpers/cpa_rank_curve.py`

## Capture command (no stage movement)
```bash
python xyz-stage/capture_cpa_current_position.py --point-index 768 --trace-count 5000
```

Optional explicit fixed key:
```bash
python xyz-stage/capture_cpa_current_position.py \
  --point-index 768 \
  --trace-count 5000 \
  --key-hex 00112233445566778899AABBCCDDEEFF
```

## What capture script writes
- Trace file: default stem is `768_cpa` (TRS output).
- Metadata JSON: `<stem>_capture_meta.json` with:
  - `point_index`
  - `trace_count`
  - `plaintext_mode` (`random`)
  - `fixed_key_hex`
  - `trace_path`
  - `output_folder`
  - `filename_stem`

## Operator window selection
```bash
python sca-helpers/plot.py /path/to/768_cpa.trs -n 5
```

## CPA rank-curve command (manual window)
```bash
python sca-helpers/cpa_rank_curve.py \
  --trs /path/to/768_cpa.trs \
  --sample-from <START> \
  --sample-to <END> \
  --step 100
```

## Aggregate curve definition used
- Main aggregate metric: **mean byte rank** across 16 AES key bytes.
- Additional tracked metric: **worst-byte rank**.
- Also reported: number of bytes with rank `0` at each trace count.
- Rank interpretation:
  - `0` = correct key byte guess is best.
  - Lower is better.

## Output artifacts from CPA analysis
For input `.../768_cpa.trs`, default outputs are:
- `.../768_cpa_cpa_rank_curve.csv`
- `.../768_cpa_cpa_rank_curve.png`
- `.../768_cpa_cpa_rank_curve.json`

CSV columns:
- `traces`
- `mean_rank`
- `worst_rank`
- `correct_bytes`

## Notes on behavior and scope
- This dedicated CPA capture path does not run XY scan logic.
- The measurement script on this branch captures fixed-key random-plaintext traces by default (TVLA acquisition branch removed).
