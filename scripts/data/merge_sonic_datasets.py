import json
import shutil
from pathlib import Path

import pandas as pd

src_roots = [
    Path("data/sonic/lerobot/2026-07-09-14-16-50"),
    Path("data/sonic/lerobot/2026-07-09-15-01-05"),
]
out_root = Path("data/sonic/lerobot/pick_up_tape")

if out_root.exists():
    raise SystemExit(f"{out_root} already exists. Rename or remove it first.")

(out_root / "data" / "chunk-000").mkdir(parents=True)
(out_root / "videos" / "chunk-000" / "observation.images.egocentric").mkdir(parents=True)
(out_root / "meta").mkdir(parents=True)

episodes_meta = []
tasks_meta = []
episode_out = 0
dataset_cursor = 0

for new_task_index, src_root in enumerate(src_roots):
    source_tasks = [
        json.loads(line)
        for line in (src_root / "meta" / "tasks.jsonl").read_text().splitlines()
        if line.strip()
    ]
    task_text = source_tasks[0]["task"]

    tasks_meta.append({
        "task_index": new_task_index,
        "task": task_text,
        "category": "default",
        "description": task_text,
    })

    for parquet_file in sorted((src_root / "data").glob("chunk-*/episode_*.parquet")):
        old_episode = int(parquet_file.stem.split("_")[1])

        video_file = (
            src_root / "videos" / f"chunk-{old_episode // 1000:03d}"
            / "observation.images.egocentric"
            / f"episode_{old_episode:06d}.mp4"
        )
        if not video_file.exists():
            raise FileNotFoundError(video_file)

        df = pd.read_parquet(parquet_file)
        length = len(df)

        df["episode_index"] = episode_out
        df["task_index"] = new_task_index
        df["index"] = list(range(length))

        out_parquet = (
            out_root / "data" / "chunk-000" / f"episode_{episode_out:06d}.parquet"
        )
        df.to_parquet(out_parquet, index=False)

        out_video = (
            out_root / "videos" / "chunk-000" / "observation.images.egocentric"
            / f"episode_{episode_out:06d}.mp4"
        )
        shutil.copy2(video_file, out_video)

        episodes_meta.append({
            "episode_index": episode_out,
            "tasks": [new_task_index],
            "length": length,
            "dataset_from_index": dataset_cursor,
            "dataset_to_index": dataset_cursor + length - 1,
            "robot_type": "g1",
            "instruction": task_text,
        })

        dataset_cursor += length
        episode_out += 1

(out_root / "meta" / "tasks.jsonl").write_text(
    "".join(json.dumps(x) + "\n" for x in tasks_meta)
)
(out_root / "meta" / "episodes.jsonl").write_text(
    "".join(json.dumps(x) + "\n" for x in episodes_meta)
)

info = {
    "codebase_version": "v2.1",
    "robot_type": "g1",
    "total_episodes": episode_out,
    "total_frames": dataset_cursor,
    "total_tasks": len(tasks_meta),
    "total_videos": episode_out,
    "total_chunks": 1,
    "chunks_size": 1000,
    "fps": 30,
    "data_path": "data/chunk-{episode_chunk:03d}/episode_{episode_index:06d}.parquet",
    "video_path": "videos/chunk-{episode_chunk:03d}/{video_key}/episode_{episode_index:06d}.mp4",
}
(out_root / "meta" / "info.json").write_text(json.dumps(info, indent=2))

print(f"Merged {episode_out} episodes into {out_root}")
