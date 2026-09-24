# SONIC to Ψ0 Fine-Tuning Guide


Set the common paths used below:

```bash
cd /home/liyan/Psi0
export PSI_HOME=/home/liyan/Psi0
export task=merged_orange
```

## 1. Merge SONIC recording sessions

Activate the data-collection environment and run the processor from the SONIC repository:

```bash
cd "$PSI_HOME/third_party/GR00T-WholeBodyControl"
source .venv_data_collection/bin/activate

python gear_sonic/scripts/process_dataset.py \
  --dataset-path \
    outputs/2026-07-24-16-59-38 \
    outputs/2026-07-25-15-12-42 \
    outputs/2026-07-25-16-22-27 \
    outputs/2026-07-24-17-08-05 \
    outputs/2026-07-25-15-25-17 \
    outputs/2026-07-25-16-34-58 \
    outputs/2026-07-25-14-52-14 \
    outputs/2026-07-25-14-52-14 \
    outputs/2026-07-25-15-42-38 \
  --output-path outputs/merged_orange

```

The processor removes discarded episodes and stale SMPL frames by default. It does not modify the source datasets.



## 2. Set the training prompt

Update the prompt in both source metadata files:

```text
third_party/GR00T-WholeBodyControl/outputs/merged_2026-07-15_to_2026-07-17/meta/tasks.jsonl
third_party/GR00T-WholeBodyControl/outputs/merged_2026-07-15_to_2026-07-17/meta/episodes.jsonl
```


```json
{"task_index": 0, "task": "Walk forward, pick up the box with both hands, step back, turn left, and place the box on the table."}
```


## 3. Convert SONIC data to the Ψ0 LeRobot schema

The merged SONIC dataset is already LeRobot v2.1, but Ψ0 requires different state, action, and camera fields. Convert the merged dataset once:

```bash
cd "$PSI_HOME"
source .venv-psi/bin/activate

python scripts/data/raw_sonic_to_psi_lerobot.py \
  --data-root="$PSI_HOME/third_party/GR00T-WholeBodyControl/outputs/$task" \
  --work-dir="$PSI_HOME/data/sonic/lerobot" \
  --repo-id="$task" \
  --robot-type=g1
```

Converted output:

```text
/home/liyan/Psi0/data/sonic/lerobot/merged_2026-07-15_to_2026-07-17
```

## 4. Calculate Ψ0 dataset statistics

```bash
python scripts/data/calc_modality_stats.py \
  --task-dir="$PSI_HOME/data/sonic/lerobot/$task"

cp "$PSI_HOME/data/sonic/lerobot/$task/meta/stats.json" \
   "$PSI_HOME/data/sonic/lerobot/$task/meta/stats_psi0.json"
```

The copy is required because the training configuration expects `meta/stats_psi0.json`.

## 5. Verify the converted dataset

```bash
DATASET="$PSI_HOME/data/sonic/lerobot/$task"

jq '{total_episodes, total_frames, total_tasks}' "$DATASET/meta/info.json"
jq -s 'map(.task) | unique' "$DATASET/meta/tasks.jsonl"
jq -s 'map(.instruction) | unique' "$DATASET/meta/episodes.jsonl"
ls -lh "$DATASET/meta/stats.json" "$DATASET/meta/stats_psi0.json"
```

Expected counts:

```text
total_episodes: 34
total_frames: 30816
total_tasks: 1
```

## 6. Check the training prerequisites



## 7. Fine-tune Ψ0

Run from the Ψ0 repository root.

One GPU:

```bash
cd "$PSI_HOME"

CUDA_VISIBLE_DEVICES=0 \
bash scripts/train/psi0/finetune-real-sonic-psi0.sh \
  "$task" \
  orange-box-pickup
```


The first argument is the dataset directory name. The second is the experiment name; it does not change the language instruction.

The current launcher configuration:

- trains for 40,000 steps;
- validates every 1,000 steps;
- saves every 5,000 steps;
- keeps five checkpoints;
- uses BF16 mixed precision;
- uses a training batch size of 64 per process.

If training runs out of GPU memory, reduce this setting in `scripts/train/psi0/finetune-real-sonic-psi0.sh`:

```bash
--train.train_batch_size=64
```

Try `8`, then `4` or `2` if necessary. Do not change gradient accumulation unless you intentionally want to change the effective batch size.

## 8. Monitor and select a checkpoint

Monitor training and validation loss in the terminal or W&B. Prefer a checkpoint with good validation loss rather than automatically assuming the final checkpoint is best.

The training log prints the exact run directory as:

```text
Accelerator runs in: <run-directory>
```

Record that directory and the selected checkpoint step for deployment.

## 9. Serve the trained policy

Set the run directory and checkpoint step selected above:

```bash
cd "$PSI_HOME"

export CHECKPOINT_DIR=/absolute/path/to/the/training/run
export CHECKPOINT_STEP=40000

bash scripts/deploy/serve_psi0-rtc-sonic.sh
```

The server listens on port `8014` by default. Test the resulting policy cautiously, with the robot workspace clear and an operator ready to stop execution.

## Quick restart point

The current dataset has already been merged, converted, assigned the new prompt, and given `stats_psi0.json`. Therefore, the current workflow can start directly at **Step 6**, followed by the fine-tuning command in **Step 7**.
