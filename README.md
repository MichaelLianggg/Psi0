# Ψ0 + SONIC on Unitree G1

End-to-end instructions for collecting demonstrations with SONIC teleoperation, converting the recorded data to the Ψ0 LeRobot schema, fine-tuning Ψ0, and deploying the resulting policy on a real Unitree G1 with DEX1 grippers and a RealSense camera.

This README covers four stages:

1. SONIC teleoperation and data collection.
2. Dataset merge, prompt setup, conversion, statistics, and verification.
3. Ψ0 fine-tuning and checkpoint selection.
4. Real-robot deployment and shutdown.

> [!WARNING]
> This guide controls a physical robot. Secure the G1 to the gantry before operation, keep the workspace clear, make sure a physical emergency stop is accessible, and keep personnel outside the robot's motion envelope while the controller is active. The software stop commands documented below are operational controls and should not be treated as a replacement for the robot's physical emergency-stop procedure. Stop the run if camera, network, controller, or state feedback becomes unstable.

## Prerequisites

### Hardware

- Unitree G1 robot secured to a gantry.
- DEX1 grippers.
- RealSense camera on the robot.
- PICO setup for teleoperation.
- Workstation with an NVIDIA GPU suitable for Ψ0 fine-tuning/inference.
- Robot/workstation network connectivity.

### Software and environments

The commands below assume the following are already installed and configured:

- The `Psi0` repository at `/home/liyan/Psi0` (also referenced as `~/Psi0`).
- `third_party/GR00T-WholeBodyControl` and its SONIC deployment/data-collection dependencies.
- ROS 2 Foxy on the robot-side workflow used here.
- Docker and NVIDIA GPU/container support on the workstation.
- TensorRT at `~/TensorRT`.
- Conda environment `vision` on the robot.
- Ψ0 Python environment `.venv-psi`.
- SONIC data-collection environment `.venv_data_collection`.
- SONIC teleoperation environment `.venv_teleop` if simulation is used.
- `jq` for dataset verification.
- `rg` (ripgrep) for optional configuration inspection.
- Weights & Biases only if W&B logging is enabled.

Unless stated otherwise, run workstation commands from the machine that contains the `Psi0` checkout.

## Contents

- [0. End-to-End Workflow](#0-end-to-end-workflow)
- [Part I — SONIC Teleoperation & Data Collection](#part-i--sonic-teleoperation--data-collection)
- [Part II — Prepare SONIC Data for Ψ0](#part-ii--prepare-sonic-data-for-ψ0)
- [Part III — Fine-Tune Ψ0](#part-iii--fine-tune-ψ0)
- [Part IV — Deploy Fine-Tuned Ψ0 on the Real G1](#part-iv--deploy-fine-tuned-ψ0-on-the-real-g1)
- [Part V — Quick Reference](#part-v--quick-reference)
- [Important Notes](#important-notes)

---

## 0. End-to-End Workflow

```text
G1 + SONIC Teleoperation
        ↓
Record SONIC episodes
        ↓
Merge recording sessions
        ↓
Set task prompt
        ↓
Convert SONIC → Ψ0 LeRobot schema
        ↓
Calculate dataset statistics
        ↓
Verify dataset
        ↓
Fine-tune Ψ0
        ↓
Select checkpoint
        ↓
Start G1 + SONIC controller
        ↓
Start Ψ0 policy server
        ↓
Start SONIC communication client
        ↓
Real-robot inference
```

---

## Part I — SONIC Teleoperation & Data Collection

### 1. Start the G1 Robot

1. Secure the G1 robot to the gantry and make sure both feet are in contact with the ground.

2. Press the power button briefly, then press and hold it again until the blue light on the head turns on and stops blinking.

3. Wait for calibration to finish. The robot light should then turn **purple**.

---

### 2. Robot Terminal 1 — Start the RealSense Camera for Teleoperation

SSH into the robot:

```bash
ssh unitree@192.168.123.164
```

Password:

```text
123
```

If prompted to select the ROS version, choose:

```text
1
```

for ROS 2 Foxy.

Start the camera:

```bash
conda activate vision
cd ~/SONIC_psi0_release
python -m gear_sonic.camera.composed_camera --ego-view-camera realsense --port 5555
```

Check that port `5555` is listening:

```bash
ss -ltnp | grep :5555
```

If an old process is occupying the port:

```bash
kill -9 <PID>
```

Keep this terminal running.

---

### 3. Robot Terminal 2 — Start the DEX1 Gripper Server

Open another terminal connected to the robot and run:

```bash
cd dex1_1_service/bin
sudo ./dex1_1_gripper_server --network eth0
```

Keep this terminal running.

---

### 4. Workstation Terminal 1 — Start the SONIC Controller

```bash
cd ~/Psi0/third_party/GR00T-WholeBodyControl/gear_sonic_deploy
export TensorRT_ROOT=$HOME/TensorRT
./docker/run-ros2-dev.sh
```

Inside the container:

```bash
source scripts/setup_env.sh
./deploy.sh --input-type zmq_manager real --hand-type dex1
```

Wait until you see:

```text
Init done
```

Keep this terminal running.

---

### 5. Workstation Terminal 2 — Start PICO Teleoperation

```bash
cd ~/Psi0
bash ./real/SONIC/scripts/collect_psi0-sonic-data-manual.sh pico
```

Alternative mirrored mode:

```bash
bash ./real/SONIC/scripts/collect_psi0-sonic-data-manual.sh pico_mirror
```

Keep this terminal running.

---

### 6. Workstation Terminal 3 — Start the Data Exporter

```bash
cd ~/Psi0
bash ./real/SONIC/scripts/collect_psi0-sonic-data-manual.sh exporter
```

Keep this terminal running.

---

### 7. Start Teleoperation

After all robot-side and workstation-side processes above are running:

1. Put the robot in the calibration pose.

2. Press:

```text
A + B + X + Y
```

This performs calibration / engages the policy state.

3. Press:

```text
A + X
```

to enable teleoperation / toggle into POSE mode.

#### Controller Shortcuts

| Action | Button | Notes |
|---|---|---|
| **Start / Stop policy** | **A+B+X+Y** | First press: engage + CALIB_FULL. Again: emergency stop → OFF. |
| **Toggle POSE** | **A+X** | Switches between PLANNER ↔ POSE. Or from VR_3PT entered through PLANNER → POSE. |
| **Toggle PLANNER_FROZEN_UPPER** | **B+Y** | Switches between POSE ↔ PLANNER_FROZEN_UPPER. Or from VR_3PT entered through PLANNER_FROZEN_UPPER → POSE. |

---

### 8. Record Episodes

Start / stop recording:

```text
Left Grip + A
```

Discard the current episode:

```text
Left Grip + B
```

Repeat the task for as many successful episodes as needed.

---

### 9. Teleoperation Checklist

**Robot**

- [ ] Camera running.
- [ ] DEX1 server running.

**Workstation**

- [ ] Terminal 1: SONIC controller → `Init done`.
- [ ] Terminal 2: PICO teleoperation running.
- [ ] Terminal 3: exporter running.

---

### 10. Optional — Run SONIC in Simulation

Start the simulator:

```bash
cd ~/Psi0/third_party/GR00T-WholeBodyControl
source .venv_teleop/bin/activate
python gear_sonic/scripts/run_sim_loop.py
```

In the deploy terminal use:

```bash
./deploy.sh --input-type zmq_manager sim
```

---

## Part II — Prepare SONIC Data for Ψ0

### 11. Set Common Paths

Set the common paths used by the dataset and training commands:

```bash
cd /home/liyan/Psi0
export PSI_HOME=/home/liyan/Psi0
export task=merged_orange
```

`$task` is used later as the merged dataset directory / repo ID. Keep this value unchanged throughout merge, conversion, training, and verification for a single experiment.

---

### 12. Merge SONIC Recording Sessions

Activate the data-collection environment:

```bash
cd "$PSI_HOME/third_party/GR00T-WholeBodyControl"
source .venv_data_collection/bin/activate
```

Merge the selected recording sessions:

```bash
python gear_sonic/scripts/process_dataset.py \
  --dataset-path \
    outputs/2026-07-24-16-59-38 \
    outputs/2026-07-25-15-12-42 \
    outputs/2026-07-25-16-22-27 \
    outputs/2026-07-24-17-08-05 \
    outputs/2026-07-25-15-25-17 \
    outputs/2026-07-25-16-34-58 \
    outputs/2026-07-25-14-52-14 \
    outputs/2026-07-25-15-42-38 \
  --output-path "outputs/$task"
```

The processor removes discarded episodes and stale SMPL frames by default. It does not modify the source datasets. Before running the command, confirm that the listed recording-session directories are the sessions you want to merge.

After merging, confirm that the output directory exists before editing metadata:

```bash
ls -lah "$PSI_HOME/third_party/GR00T-WholeBodyControl/outputs/$task"
```

---

### 13. Set the Training Prompt

Update the task prompt in both metadata files in the merged dataset:

```text
$PSI_HOME/third_party/GR00T-WholeBodyControl/outputs/$task/meta/tasks.jsonl
$PSI_HOME/third_party/GR00T-WholeBodyControl/outputs/$task/meta/episodes.jsonl
```

Keep the language instruction consistent across the two metadata files. For `tasks.jsonl`, the guide provides this example entry:

```json
{"task_index": 0, "task": "Walk forward, pick up the box with both hands, step back, turn left, and place the box on the table."}
```

The source material does not provide a complete example row for `episodes.jsonl`. Preserve its existing schema and update the instruction text consistently rather than replacing the whole row with the `tasks.jsonl` example.

---

### 14. Convert SONIC Data to the Ψ0 LeRobot Schema

The merged SONIC dataset is already LeRobot v2.1, but Ψ0 requires different state, action, and camera fields.

Activate the Ψ0 environment and convert the dataset:

```bash
cd "$PSI_HOME"
source .venv-psi/bin/activate
python scripts/data/raw_sonic_to_psi_lerobot.py \
  --data-root="$PSI_HOME/third_party/GR00T-WholeBodyControl/outputs/$task" \
  --work-dir="$PSI_HOME/data/sonic/lerobot" \
  --repo-id="$task" \
  --robot-type=g1
```

The converted dataset is written to:

```text
$PSI_HOME/data/sonic/lerobot/$task
```

With the example values in Section 11, this resolves to:

```text
/home/liyan/Psi0/data/sonic/lerobot/merged_orange
```

---

### 15. Calculate Ψ0 Dataset Statistics

```bash
python scripts/data/calc_modality_stats.py \
  --task-dir="$PSI_HOME/data/sonic/lerobot/$task"
cp "$PSI_HOME/data/sonic/lerobot/$task/meta/stats.json" \
   "$PSI_HOME/data/sonic/lerobot/$task/meta/stats_psi0.json"
```

The copy is required because the training configuration expects:

```text
meta/stats_psi0.json
```

---

### 16. Verify the Converted Dataset

```bash
DATASET="$PSI_HOME/data/sonic/lerobot/$task"
jq '{total_episodes, total_frames, total_tasks}' "$DATASET/meta/info.json"
jq -s 'map(.task) | unique' "$DATASET/meta/tasks.jsonl"
jq -s 'map(.instruction) | unique' "$DATASET/meta/episodes.jsonl"
ls -lh "$DATASET/meta/stats.json" "$DATASET/meta/stats_psi0.json"
```

Example counts from the dataset used when this guide was written:

```text
total_episodes: 34
total_frames: 30816
total_tasks: 1
```

These values are only an example. Newly collected datasets can have different episode and frame counts.

---

## Part III — Fine-Tune Ψ0

### 17. Optional — Configure Weights & Biases (W&B)

W&B can be used to monitor training and validation loss.

```bash
cd "$PSI_HOME"
source .venv-psi/bin/activate
pip install wandb
wandb login
```

When prompted, paste the API key from the W&B account settings page. Do not put the API key in this guide or commit it to Git.

Create a local `.env` in the Ψ0 repository root and make sure it is ignored by Git:

```bash
export WANDB_MODE=online
export WANDB_PROJECT=sonic-psi0
export WANDB_ENTITY="<your-wandb-username-or-team>"
export WANDB_NAME=orange-box-pickup
```

Load it before training:

```bash
source .env
wandb login --verify
```

If needed, check whether the training configuration reports metrics to W&B:

```bash
rg "wandb|report_to|WANDB" scripts configs
```

For a machine without network access:

```bash
export WANDB_MODE=offline
```

Later, when network access is available:

```bash
wandb sync "<offline-run-directory>"
```

---

### 18. Check Training Prerequisites

Before starting training, verify that:

- [ ] The Ψ0 environment is active: `source .venv-psi/bin/activate`.
- [ ] The converted dataset exists at `$PSI_HOME/data/sonic/lerobot/$task`.
- [ ] `meta/info.json`, `meta/tasks.jsonl`, and `meta/episodes.jsonl` are present.
- [ ] Both `meta/stats.json` and `meta/stats_psi0.json` exist.
- [ ] The dataset task/instruction values match the task you intend to train.
- [ ] The selected GPU is visible to CUDA.
- [ ] If W&B logging is enabled, the W&B environment variables are loaded and authentication succeeds.

The verification commands in Section 16 should complete successfully before training.

---

### 19. Fine-Tune Ψ0

Run from the Ψ0 repository root.

Single GPU example:

```bash
cd "$PSI_HOME"
CUDA_VISIBLE_DEVICES=0 \
bash scripts/train/psi0/finetune-real-sonic-psi0.sh \
  "$task" \
  orange-box-pickup
```

Arguments:

```text
1st argument: dataset directory name
2nd argument: experiment name
```

The experiment name does **not** change the language instruction stored in the dataset metadata.

#### If GPU Memory Is Insufficient

The training script contains:

```bash
--train.train_batch_size=64
```

If training runs out of GPU memory, try reducing the batch size to:

```text
8
4
2
```

Do not change gradient accumulation unless you intentionally want to change the effective batch size.

---

### 20. Monitor Training and Select a Checkpoint

Monitor training and validation loss in the terminal or W&B.

Select a checkpoint with good validation loss rather than automatically assuming the final checkpoint is the best one.

The training log prints the run directory as:

```text
Accelerator runs in: <run-directory>
```

Record both:

```text
CHECKPOINT_DIR=<run-directory>
CHECKPOINT_STEP=<selected-step>
```

You will use them in deployment.

---

## Part IV — Deploy Fine-Tuned Ψ0 on the Real G1

> [!NOTE]
> This section uses the **deployment-specific** camera and SONIC controller commands. They are different from the teleoperation/data-collection commands in Part I.

### 21. Start the G1 Robot

1. Secure the G1 robot to the gantry and make sure both feet are in contact with the ground.

2. Press the power button briefly, then press and hold it again until the blue light on the head turns on and stops blinking.

3. Wait for calibration to finish. The robot light should then turn **purple**.

---

### 22. Robot Terminal 1 — Start the Deployment RealSense Camera Server

SSH into the robot:

```bash
ssh unitree@192.168.123.164
```

Password:

```text
123
```

If prompted, choose:

```text
1
```

for ROS 2 Foxy.

Start the deployment camera server:

```bash
conda activate vision
cd ~/SONIC_psi0_release
python realsense_server.py
```

If an old video hub process is running, stop it before restarting the camera server:

```bash
sudo pkill -f videohub_pc4
```

Keep this terminal running.

---

### 23. Robot Terminal 2 — Start the DEX1 Gripper Server

Open another terminal connected to the robot:

```bash
ssh unitree@192.168.123.164
```

Start the gripper server:

```bash
cd dex1_1_service/bin
sudo ./dex1_1_gripper_server --network eth0
```

Keep this terminal running.

---

### 24. Workstation Terminal 1 — Start the SONIC Controller for Deployment

If Docker permission has not been configured for the current user, run once:

```bash
sudo usermod -aG docker $USER
newgrp docker
```

Set TensorRT and start the ROS 2 development container:

```bash
export TensorRT_ROOT=~/TensorRT
cd ~/Psi0/third_party/GR00T-WholeBodyControl/gear_sonic_deploy
./docker/run-ros2-dev.sh
```

Inside the container:

```bash
source scripts/setup_env.sh
./deploy.sh real --hand-type dex1
```

Wait until you see:

```text
Init done
```

Then, in the same terminal:

1. Press `#` to set the robot upright.

2. Press `]` after the robot has reached the required position. The robot will stand up when you press `]`.

3. Wait until you see:

```text
transitioning to CONTROL state
```

4. Press **Enter**.

5. Wait until you see:

```text
ZMQ STREAMING MODE: ENABLED
```

Keep this terminal running.

---

### 25. Workstation Terminal 2 — Start the Ψ0 Policy Server

The policy server loads the trained Ψ0 checkpoint on the GPU, receives observations, and predicts actions.

Go to the Ψ0 repository:

```bash
cd ~/Psi0
```

Set the selected checkpoint directory and step.

Example checkpoint configuration:

```bash
export CHECKPOINT_DIR="$HOME/Psi0/.runs/sonic/orange-box-pickup.real.flow1000.cosine.lr1.0e-04.b64.gpus1.2607262327"
export CHECKPOINT_STEP=50000
```

For a newly trained model, replace those values with the run directory and checkpoint step selected in Part III.

Start the policy server:

```bash
bash ./scripts/deploy/serve_psi0-rtc-sonic.sh
```

Wait until the policy server is ready before starting the communication client.

Keep this terminal running.

---

### 26. Workstation Terminal 3 — Start the SONIC Communication Client

The communication client:

```text
G1 camera + robot state
        ↓
SONIC communication client
        ↓
Ψ0 policy server
        ↓
predicted actions
        ↓
SONIC communication client
        ↓
G1 controller
```

Start it with:

```bash
cd ~/Psi0
bash ./real/scripts/deploy_psi0-sonic-rtc-client.sh
```

Keep this terminal running during inference.

---

### 27. Deployment Checklist

Before starting inference, verify:

**Robot**

- [ ] RealSense camera server running.
- [ ] DEX1 gripper server running.

**Workstation**

- [ ] SONIC controller reached `Init done`.
- [ ] `CONTROL` state entered.
- [ ] `ZMQ STREAMING MODE: ENABLED`.
- [ ] Ψ0 policy server ready.
- [ ] SONIC communication client running.

---

### 28. Stop Deployment

#### Normal Stop

Go to the **SONIC Communication Client** terminal and press:

```text
Ctrl+C
```

The communication client stops and robot motion stops.

#### Emergency Stop

Go to the **SONIC Controller** terminal and press:

```text
o
```

The robot enters damping mode.

After robot motion has stopped, terminate the remaining policy server, camera, gripper, and controller processes as appropriate for your setup.

---

## Part V — Quick Reference

### Teleoperation / Data Collection Processes

| Machine | Terminal | Process |
|---|---|---|
| Robot | 1 | `composed_camera` RealSense server on port 5555 |
| Robot | 2 | DEX1 gripper server |
| Workstation | 1 | SONIC controller with `--input-type zmq_manager real` |
| Workstation | 2 | PICO / PICO mirror teleoperation |
| Workstation | 3 | Data exporter |

### Ψ0 Deployment Processes

| Machine | Terminal | Process |
|---|---|---|
| Robot | 1 | `realsense_server.py` |
| Robot | 2 | DEX1 gripper server |
| Workstation | 1 | SONIC controller with `./deploy.sh real --hand-type dex1` |
| Workstation | 2 | Ψ0 policy server |
| Workstation | 3 | SONIC communication client |

### Dataset / Training Flow

```text
SONIC recording directories
    ↓ process_dataset.py
merged SONIC dataset
    ↓ edit tasks.jsonl / episodes.jsonl
language instruction
    ↓ raw_sonic_to_psi_lerobot.py
Ψ0 LeRobot dataset
    ↓ calc_modality_stats.py
stats.json + stats_psi0.json
    ↓ finetune-real-sonic-psi0.sh
training run
    ↓ select validation checkpoint
CHECKPOINT_DIR + CHECKPOINT_STEP
    ↓ serve_psi0-rtc-sonic.sh
Ψ0 policy server
```


