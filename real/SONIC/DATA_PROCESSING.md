# Process SONIC Data for Ψ₀

Use this order:

```text
clean and merge → update prompt → convert → calculate stats → train
```

> Clean the original SONIC recordings before conversion. Discarded episodes are flagged in `meta/info.json`, but the Ψ₀ converter does not preserve or filter those flags.

## 1. Set the dataset names

Run from the Ψ₀ repository:

```bash
export PSI_HOME="$PWD"
export SESSION_1=2026-07-09-14-16-50
export SESSION_2=2026-07-09-15-01-05
export DATASET_NAME=pick_up_tape_cleaned
```

## 2. Clean and merge

This removes discarded episodes while keeping the original recordings unchanged:

```bash
cd "$PSI_HOME/third_party/GR00T-WholeBodyControl"
source .venv_data_collection/bin/activate

python gear_sonic/scripts/process_dataset.py \
  --dataset-path "outputs/$SESSION_1" "outputs/$SESSION_2" \
  --output-path "outputs/$DATASET_NAME" \
  --no-remove-stale-smpl
```

For the example sessions, the cleaned result should have 40 episodes and 26,152 frames:

```bash
jq '{total_episodes, total_frames}' "outputs/$DATASET_NAME/meta/info.json"
```

## 3. Update the prompt

Before conversion, update the cleaned dataset so that:

- `meta/tasks.jsonl`: `task` contains the new prompt.
- `meta/episodes.jsonl`: every `tasks` value is `["<new prompt>"]`.

Both files are under:

```text
third_party/GR00T-WholeBodyControl/outputs/$DATASET_NAME/meta/
```

## 4. Convert to the Ψ₀ format

```bash
cd "$PSI_HOME"
source .venv-psi/bin/activate

python scripts/data/raw_sonic_to_psi_lerobot.py \
  --data-root="third_party/GR00T-WholeBodyControl/outputs/$DATASET_NAME" \
  --work-dir="$PSI_HOME/data/sonic/lerobot" \
  --repo-id="$DATASET_NAME" \
  --robot-type=g1
```

The result is written to:

```text
data/sonic/lerobot/$DATASET_NAME
```

## 5. Calculate statistics

```bash
python scripts/data/calc_modality_stats.py \
  --task-dir="$PSI_HOME/data/sonic/lerobot/$DATASET_NAME"

cp "$PSI_HOME/data/sonic/lerobot/$DATASET_NAME/meta/stats.json" \
   "$PSI_HOME/data/sonic/lerobot/$DATASET_NAME/meta/stats_psi0.json"
```

The copy is needed because the calculator creates `stats.json`, while Ψ₀ training expects `stats_psi0.json`.

## 6. Verify and train

```bash
DATASET="$PSI_HOME/data/sonic/lerobot/$DATASET_NAME"

jq '{total_episodes, total_frames, total_tasks}' "$DATASET/meta/info.json"
jq -s 'map(.task) | unique' "$DATASET/meta/tasks.jsonl"
jq -s 'map(.instruction) | unique' "$DATASET/meta/episodes.jsonl"
```

Make sure `--data.root_dir` in `scripts/train/psi0/finetune-real-sonic-psi0.sh` points to `$PSI_HOME/data/sonic/lerobot`, then run:

```bash
CUDA_VISIBLE_DEVICES=0 \
  bash scripts/train/psi0/finetune-real-sonic-psi0.sh \
  "$DATASET_NAME" pick-up-tape
```
