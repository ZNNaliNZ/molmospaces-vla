# Multi-Embodiment Tabletop Data Generation Plan

## Objective

Generate reproducible demonstrations for five tabletop task families across every bundled
manipulation-capable embodiment:

- `pick`
- `pick_and_place`
- `pick_and_place_next_to`
- `pick_and_place_color`
- `packing`

The target matrix contains 45 cells: five tasks by nine embodiment profiles.

## Scope

The first implementation covers these built-in embodiment profiles:

1. Franka DROID
2. Mobile Franka
3. Franka CAP
4. RB-Y1
5. RB-Y1M
6. Floating RUM
7. Floating Robotiq 2F-85
8. I2RT YAM
9. Bimanual I2RT YAM

`RBY1MOpenCloseConfig` is a control-mode variant rather than another embodiment. The XArm7
tutorial is excluded from the default matrix because its robot assets are supplied externally.

For dual-arm embodiments, the initial atomic-task implementation uses one active arm per run.
Separate left- and right-arm runs should be balanced in the final dataset. Coordinated bimanual
behavior is outside this plan.

## Readiness levels

Every matrix cell carries one of these readiness labels:

- `reference`: established configuration used as the baseline.
- `existing`: the repository already contains a closely matching data-generation path.
- `pilot`: the common interface is implemented, but the combination needs a pilot rollout.
- `adapter`: an embodiment-specific planner, camera, grasp, or control adapter is still required.

The matrix launcher refuses non-reference/non-existing cells unless the caller explicitly passes
`--allow-unvalidated`.

## Implementation steps

### 1. Common task and embodiment profiles

- [x] Define one task profile for each tabletop task.
- [x] Define one embodiment profile containing robot, cameras, timing, reach, placement, and
      active-manipulator settings.
- [x] Expose all task/embodiment pairs through stable registered configuration names.
- [x] Store task, embodiment, readiness, active gripper, and matrix version in each experiment
      config.

### 2. Active manipulator support

- [x] Add an optional active gripper and active IK move groups to robot configs.
- [x] Make task sampling, grasp selection, sensors, and generic planners use the configured active
      gripper instead of silently selecting the first gripper.
- [x] Allow RB-Y1 and bimanual YAM runs to select left or right manipulation independently.

### 3. Planner paths

- [x] Use the generic MuJoCo IK planner for single-arm, mobile Franka, CAP, floating-gripper, YAM,
      and fallback RB-Y1 profiles.
- [x] Use the existing CuRobo pick-and-place stack for RB-Y1M.
- [x] Reuse CuRobo pick-and-place execution for color and packing tasks.
- [x] Add a next-to target adapter for the CuRobo path.

### 4. Camera and sampling profiles

- [x] Reuse native Franka, RB-Y1, and YAM camera systems.
- [x] Provide common exocentric cameras for floating grippers.
- [x] Apply per-embodiment reach, safety-radius, and vertical-placement overrides.
- [ ] Calibrate wrist-camera extrinsics and TCP/grasp transforms from rendered pilot episodes.

### 5. Matrix launcher

- [x] List supported combinations and readiness without loading simulation assets.
- [x] Validate configuration construction before rollout.
- [x] Select tasks, embodiments, active grippers, houses, seeds, samples, and output roots.
- [x] Require explicit authorization for unvalidated combinations.
- [x] Support resume through the existing per-house batch output behavior.

### 6. Validation funnel

Run these gates for every matrix cell before production:

1. Construct the configuration and resolve its assets.
2. Sample at least 20 target poses and inspect IK/reach failures.
3. Run 20 attempted smoke-test episodes.
4. Generate 100 successful pilot episodes.
5. Review at least 10 videos manually.
6. Check task-oracle success, target visibility, action/state integrity, video length, NaNs, and
   output metadata.

Use `scripts/data/validate_trajectories.py` for structural/video validation and
`scripts/data/calculate_stats.py` for per-task, per-embodiment statistics.

### 7. Production rollout

Scale in this order:

1. All five tasks on Franka DROID.
2. All five tasks on RB-Y1M.
3. Floating RUM, Floating Robotiq, Franka CAP, Mobile Franka, and single-arm YAM.
4. RB-Y1 and Bimanual YAM, with balanced left/right runs.

Balance the final dataset by successful trajectories rather than attempted episodes. Keep scene
and object splits disjoint between train, validation, and test. Preserve native move-group-keyed
actions in raw data; any fixed-width cross-embodiment representation should be a downstream
conversion.

## Usage

List the matrix:

```bash
python scripts/datagen/run_tabletop_matrix.py --list
```

Validate configuration construction for one cell:

```bash
python scripts/datagen/run_tabletop_matrix.py \
  --task pick_and_place \
  --embodiment franka_droid \
  --validate-only
```

Run a small pilot:

```bash
python scripts/datagen/run_tabletop_matrix.py \
  --task pick_and_place \
  --embodiment franka_droid \
  --samples-per-house 2 \
  --max-tasks 20 \
  --house-indices 0 1 2 3
```

An unvalidated cell additionally requires `--allow-unvalidated`.

After every cell has passed its pilot gate, the complete matrix can be selected with
`--all --allow-unvalidated --balance-arms`. The arm-balancing flag creates separate left/right
output directories for dual-arm embodiments. Keep a bounded `--max-tasks` until storage and
throughput have been confirmed.

## Definition of done

The project is production-ready when every intended matrix cell has a constructible config,
passing integration coverage, reviewed pilot videos, recorded raw-yield metrics, and validated
balanced output. Large-scale generation is deliberately not triggered by repository setup: the
operator must choose episode counts, assets, output storage, and compute allocation explicitly.
