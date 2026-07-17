"""List, validate, and run the multi-embodiment tabletop datagen matrix."""

from __future__ import annotations

import argparse
import datetime
import json
import logging
from pathlib import Path
import subprocess

from molmo_spaces.data_generation.config.tabletop_datagen_configs import (
    TABLETOP_EMBODIMENT_PROFILES,
    TABLETOP_TASK_PROFILES,
    TabletopCombination,
    TabletopReadiness,
    build_tabletop_config,
    list_tabletop_combinations,
)
log = logging.getLogger(__name__)


def _combination_lookup() -> dict[tuple[str, str], TabletopCombination]:
    return {
        (combination.task.key, combination.embodiment.key): combination
        for combination in list_tabletop_combinations()
    }


def _print_matrix() -> None:
    rows = [
        (
            combination.task.key,
            combination.embodiment.key,
            combination.readiness.value,
            combination.config_name,
        )
        for combination in list_tabletop_combinations()
    ]
    headers = ("task", "embodiment", "readiness", "registered config")
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]
    print("  ".join(value.ljust(widths[index]) for index, value in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the MolmoSpaces tabletop task-by-embodiment matrix."
    )
    parser.add_argument("--list", action="store_true", help="List all matrix cells and exit.")
    parser.add_argument("--all", action="store_true", help="Select the complete 40-cell matrix.")
    parser.add_argument(
        "--task",
        nargs="+",
        choices=tuple(TABLETOP_TASK_PROFILES),
        help="One or more tabletop tasks.",
    )
    parser.add_argument(
        "--embodiment",
        nargs="+",
        choices=tuple(TABLETOP_EMBODIMENT_PROFILES),
        help="One or more embodiment profiles.",
    )
    parser.add_argument(
        "--active-gripper",
        choices=("left", "right", "left_gripper", "right_gripper", "gripper"),
        help="Override the active gripper for a single selected embodiment.",
    )
    parser.add_argument(
        "--balance-arms",
        action="store_true",
        help="Run both active-gripper variants for every dual-arm embodiment.",
    )
    parser.add_argument(
        "--allow-unvalidated",
        action="store_true",
        help="Allow cells marked pilot.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Construct configs and resolve dependencies without sampling episodes.",
    )
    parser.add_argument("--scene-dataset", default="procthor-10k")
    parser.add_argument("--data-split", default="train", choices=("train", "val", "test"))
    parser.add_argument("--seed", type=int)
    parser.add_argument("--num-workers", type=int, default=1)
    parser.add_argument("--samples-per-house", type=int, default=20)
    parser.add_argument("--max-tasks", type=int, default=100)
    parser.add_argument("--house-indices", type=int, nargs="+")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("experiment_output/tabletop"),
        help="Each cell writes to <root>/<embodiment>/<task>.",
    )
    parser.add_argument(
        "--run-name",
        help="Optional directory below each task; omit it to resume the stable cell directory.",
    )
    parser.add_argument("--viewer", action="store_true")
    return parser.parse_args()


def _selected_cells(args: argparse.Namespace) -> list[TabletopCombination]:
    if args.all:
        if args.task or args.embodiment:
            raise ValueError("--all cannot be combined with --task or --embodiment")
        return list_tabletop_combinations()
    if not args.task or not args.embodiment:
        raise ValueError("--task and --embodiment are required unless --list or --all is used")
    lookup = _combination_lookup()
    return [lookup[(task, embodiment)] for task in args.task for embodiment in args.embodiment]


def _is_unvalidated(combination: TabletopCombination) -> bool:
    return combination.readiness is TabletopReadiness.PILOT


def _source_revision() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _write_run_manifest(config, combination: TabletopCombination) -> None:
    manifest = {
        "created_at_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "matrix_version": config.tabletop_matrix_version,
        "source_revision": config.tabletop_source_revision,
        "task": combination.task.key,
        "embodiment": combination.embodiment.key,
        "readiness": combination.readiness.value,
        "active_gripper_move_group_id": config.robot_config.active_gripper_move_group_id,
        "active_ik_move_group_ids": config.robot_config.active_ik_move_group_ids,
        "scene_dataset": config.scene_dataset,
        "data_split": config.data_split,
        "seed": config.seed,
        "resource_versions": config.tabletop_resource_versions,
        "camera_roles": config.tabletop_camera_roles,
        "samples_per_house": config.task_sampler_config.samples_per_house,
        "max_tasks": config.task_sampler_config.max_tasks,
        "house_inds": config.task_sampler_config.house_inds,
    }
    with open(config.output_dir / "tabletop_run_manifest.json", "w") as manifest_file:
        json.dump(manifest, manifest_file, indent=2, sort_keys=True)
        manifest_file.write("\n")


def main() -> None:
    args = _parse_args()
    logging.basicConfig(level=logging.INFO)

    if args.list:
        _print_matrix()
        return

    cells = _selected_cells(args)
    if args.active_gripper and args.balance_arms:
        raise ValueError("--active-gripper and --balance-arms are mutually exclusive")
    if args.active_gripper and len({cell.embodiment.key for cell in cells}) != 1:
        raise ValueError("--active-gripper can only be used with one embodiment")
    expanded_cell_count = sum(
        len(cell.embodiment.active_gripper_ids) if args.balance_arms else 1 for cell in cells
    )
    if args.viewer and expanded_cell_count != 1:
        raise ValueError("--viewer can only be used with one matrix cell")

    blocked = [cell for cell in cells if _is_unvalidated(cell)]
    if blocked and not args.allow_unvalidated:
        blocked_names = ", ".join(
            f"{cell.task.key}/{cell.embodiment.key} ({cell.readiness.value})" for cell in blocked
        )
        raise ValueError(
            f"Refusing unvalidated matrix cells: {blocked_names}. "
            "Run pilots explicitly with --allow-unvalidated."
        )

    source_revision = _source_revision()
    for cell in cells:
        active_grippers = (
            cell.embodiment.active_gripper_ids
            if args.balance_arms
            else (args.active_gripper,)
        )
        for active_gripper in active_grippers:
            output_dir = args.output_root / cell.embodiment.key / cell.task.key
            if args.balance_arms and len(cell.embodiment.active_gripper_ids) > 1:
                arm_name = active_gripper.removesuffix("_gripper")
                output_dir /= f"active_{arm_name}"
            if args.run_name:
                output_dir /= args.run_name

            log.info(
                "Preparing task=%s embodiment=%s readiness=%s active_gripper=%s",
                cell.task.key,
                cell.embodiment.key,
                cell.readiness.value,
                active_gripper or "profile default",
            )
            config = build_tabletop_config(
                cell.task.key,
                cell.embodiment.key,
                active_gripper=active_gripper,
                scene_dataset=args.scene_dataset,
                data_split=args.data_split,
                seed=args.seed,
                output_dir=output_dir,
                num_workers=args.num_workers,
                samples_per_house=args.samples_per_house,
                max_tasks=args.max_tasks,
                house_inds=args.house_indices,
                use_passive_viewer=args.viewer,
            )
            config.tabletop_source_revision = source_revision

            if args.validate_only:
                log.info(
                    "Validated %s: robot=%s active_gripper=%s output=%s",
                    cell.config_name,
                    config.robot_config.name,
                    config.robot_config.active_gripper_move_group_id,
                    config.output_dir,
                )
                continue

            config.output_dir.mkdir(parents=True, exist_ok=True)
            _write_run_manifest(config, cell)
            config.save_config()
            from molmo_spaces.data_generation.pipeline import ParallelRolloutRunner

            success_count, total_count = ParallelRolloutRunner(config).run()
            log.info(
                "Finished %s: %s/%s successful episodes",
                cell.config_name,
                success_count,
                total_count,
            )


if __name__ == "__main__":
    main()
