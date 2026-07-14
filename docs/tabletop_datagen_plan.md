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

## Next-agent testing and debugging handoff

### Current state and guardrails

- The implementation is complete through the pre-pilot stage, but none of the new tests,
  configuration validations, or simulation rollouts have been run yet.
- Treat all `pilot` cells as unvalidated, regardless of whether their configuration constructs.
  Do not promote readiness or start production generation until the validation funnel passes.
- Start with one worker, one house, and one attempted episode. Do not begin with `--all`.
- The 45-cell matrix counts one default-arm configuration per task/embodiment pair.
  `--all --balance-arms` expands dual-arm embodiments into additional left/right runs.
- RB-Y1M uses CuRobo. Constructing that profile, including with `--validate-only`, may import
  optional CuRobo dependencies, require a suitable GPU environment, and resolve robot assets.
  The other profiles should be checked first in a CPU-only environment.
- Use a fresh `--run-name` or temporary output root while debugging. Stable output paths resume
  by skipping batches that already exist, which can hide whether a code change fixed a rollout.
- Keep native move-group-keyed actions in generated data. Do not add action padding or a shared
  fixed-width action space to the raw generation path.

### Files that define this implementation

- `molmo_spaces/data_generation/config/tabletop_datagen_configs.py`: task profiles,
  embodiment profiles, readiness, generated config classes, and the config builder.
- `scripts/datagen/run_tabletop_matrix.py`: matrix selection, safety gates, arm expansion,
  manifests, and rollout dispatch.
- `molmo_spaces/configs/robot_configs.py`: active gripper and active IK group configuration.
- `molmo_spaces/robots/robot_views/abstract.py`: runtime active-manipulator selection.
- `molmo_spaces/policy/solvers/object_manipulation/base_object_manipulation_planner_policy.py`:
  generic IK planner use of the active manipulator.
- `molmo_spaces/policy/solvers/object_manipulation/curobo_pick_and_place_next_to_planner_policy.py`:
  RB-Y1M next-to adapter.
- `mlspaces_tests/data_generation/test_tabletop_datagen_configs.py`: focused matrix/config tests.

### Test in this order

1. Check the patch before importing simulation code:

   ```bash
   git status --short
   git diff --check
   ```

2. List the matrix. This path is intended not to load simulation assets or CuRobo:

   ```bash
   python scripts/datagen/run_tabletop_matrix.py --list
   ```

   Expected result: 45 data rows, representing five tasks by nine embodiments, with stable
   config names and a readiness label on every row.

3. Run the focused unit tests, then the existing data-generation regression tests:

   ```bash
   pytest -q mlspaces_tests/data_generation/test_tabletop_datagen_configs.py
   pytest -q mlspaces_tests/data_generation/test_datagen_configs.py
   ```

4. Run targeted static checks on the new and materially changed Python files:

   ```bash
   ruff check molmo_spaces/data_generation/config/tabletop_datagen_configs.py \
     scripts/datagen/run_tabletop_matrix.py \
     mlspaces_tests/data_generation/test_tabletop_datagen_configs.py
   ruff format --check molmo_spaces/data_generation/config/tabletop_datagen_configs.py \
     scripts/datagen/run_tabletop_matrix.py \
     mlspaces_tests/data_generation/test_tabletop_datagen_configs.py
   ```

5. Construct one reference config, followed by each non-CuRobo embodiment. Add
   `--allow-unvalidated` for a `pilot` cell:

   ```bash
   python scripts/datagen/run_tabletop_matrix.py \
     --task pick --embodiment franka_droid --validate-only

   python scripts/datagen/run_tabletop_matrix.py \
     --task pick --embodiment mobile_franka --allow-unvalidated --validate-only

   python scripts/datagen/run_tabletop_matrix.py \
     --task pick --embodiment bimanual_yam --active-gripper right \
     --allow-unvalidated --validate-only
   ```

   Repeat the second pattern for `franka_cap`, `rby1`, `floating_rum`, `floating_robotiq`,
   `i2rt_yam`, and `bimanual_yam`. Exercise both arms of `rby1` and `bimanual_yam`. Then repeat
   across the five tasks. A successful construction is necessary but is not evidence that IK,
   cameras, grasps, or success predicates work in simulation.

6. In an environment with the `[curobo]` extra, a supported GPU, and available RB-Y1M assets,
   validate RB-Y1M separately:

   ```bash
   python scripts/datagen/run_tabletop_matrix.py \
     --task pick --embodiment rby1m --allow-unvalidated --validate-only
   ```

   Exercise both RB-Y1M arms before its pilot is considered complete.

7. Run the first simulation smoke test with a single process and a fresh output directory:

   ```bash
   MUJOCO_GL=egl PYOPENGL_PLATFORM=egl \
   python scripts/datagen/run_tabletop_matrix.py \
     --task pick \
     --embodiment franka_droid \
     --house-indices 0 \
     --samples-per-house 1 \
     --max-tasks 1 \
     --num-workers 1 \
     --output-root /tmp/molmospaces-tabletop-smoke \
     --run-name first_pass
   ```

   Once this passes, test the remaining Franka DROID tasks in this order: `pick_and_place`,
   `pick_and_place_next_to`, `pick_and_place_color`, then `packing`. Next follow the production
   rollout order above. Add `--allow-unvalidated` for every pilot cell.

8. Only after a cell works with `--num-workers 1`, repeat a small run with two workers. This
   specifically checks that dynamically generated configuration classes remain pickle-safe:

   ```bash
   MUJOCO_GL=egl PYOPENGL_PLATFORM=egl \
   python scripts/datagen/run_tabletop_matrix.py \
     --task pick \
     --embodiment franka_droid \
     --house-indices 0 1 \
     --samples-per-house 1 \
     --max-tasks 2 \
     --num-workers 2 \
     --output-root /tmp/molmospaces-tabletop-smoke \
     --run-name two_workers
   ```

### Expected artifacts and validation

A launched cell should create the following beneath
`<output-root>/<embodiment>/<task>/<run-name>/`:

- `tabletop_run_manifest.json`, including matrix version, source revision, task, embodiment,
  readiness, active gripper, camera roles, resource versions, and sampling parameters.
- `experiment_config.pkl`.
- `running_log.log`.
- `house_<id>/trajectories*.h5` and its corresponding camera MP4 files after successful
  trajectories are saved.
- With `--balance-arms`, `active_left/` and `active_right/` directories for dual-arm profiles.

Run structural and video validation in dry-run mode first:

```bash
python scripts/data/validate_trajectories.py \
  /tmp/molmospaces-tabletop-smoke/franka_droid/pick/first_pass \
  --num-workers 1 \
  --dry-run
```

Inspect the available data keys before choosing the statistics keys for a new embodiment, then
run statistics without writing during initial debugging:

```bash
python scripts/data/view_data.py \
  /tmp/molmospaces-tabletop-smoke/franka_droid/pick/first_pass

python scripts/data/calculate_stats.py \
  /tmp/molmospaces-tabletop-smoke/franka_droid/pick/first_pass \
  --keys obs/agent/qpos obs/agent/qvel \
  --num-workers 1 \
  --dry-run
```

Also inspect at least 10 videos per pilot cell. Confirm that the commanded object, receptacle or
reference object, active gripper, and the actual success event are visible. Structural validity
alone does not catch incorrect task semantics.

### Failure-to-component debug map

| Symptom | Inspect first | Required evidence before closing |
| --- | --- | --- |
| Matrix row is missing, duplicated, or cannot be imported | Generated class registration and module globals in `tabletop_datagen_configs.py` | Exactly 45 unique config names; focused tests pass |
| Wrong arm moves or sensor labels reference the other arm | `active_gripper_move_group_id`, `active_ik_move_group_ids`, robot-view setter, and profile `active_gripper_ids` | Left/right smoke runs move only the selected arm and manifests record it |
| Target sampling repeatedly fails | Per-profile reach, safety radius, vertical placement, table bounds, and active TCP pose | At least 20 sampled targets are in bounds and reachable |
| IK fails or returns NaNs | Active IK groups, TCP transform, joint limits, grasp pose, and batch-IK support flag | Finite actions and successful IK for sampled approach/grasp/place poses |
| Object is reachable but never grasped | Grasp library compatibility, gripper TCP, finger geometry, collision masks, and close command | Stable lift in reviewed video; do not weaken the success oracle to compensate |
| Next-to episodes execute as ordinary place | Next-to planner adapter and same-support/surface-gap success checks | Placed object and reference object share support and satisfy the configured gap |
| Color task chooses the wrong receptacle | Color task sampler metadata, language fields, and receptacle selection | Manifest/task data and video agree on the requested color |
| Packing cannot sample or close around objects | Box assets, dimensions, flap state, and `packing_task_sampler.py` | Objects finish inside the intended box and oracle success matches video |
| A camera is missing, black, or does not see the target | Profile `camera_config_factory`, camera-role mapping, renderer backend, and extrinsics | Valid MP4 frames and target visibility in reviewed episodes |
| Single worker passes but multiprocessing fails | Pickling of generated config classes, lazy policy builders, and worker imports | The two-worker smoke run produces valid HDF5 and MP4 output |
| RB-Y1M import or planning fails | `[curobo]` installation, CUDA/GPU availability, asset paths, lazy CuRobo builder, and local `server_urls=[]` | Config constructs and a local CuRobo smoke episode completes; do not silently switch to a remote server |
| Rerun exits without exercising changed code | Existing `trajectories*.h5` resume behavior | Reproduce with a fresh `--run-name` or empty temporary output path |

### Per-cell debugging checklist

For every task/embodiment/active-arm cell, record all of the following before changing its
readiness:

- [ ] Config constructs and required assets resolve.
- [ ] Correct active gripper, IK groups, control mode, and camera roles appear in the manifest.
- [ ] At least 20 target poses were sampled; reach and IK failure counts were recorded.
- [ ] Cameras render finite, non-empty frames and the relevant objects are visible.
- [ ] The sampler produces the intended task semantics and language fields.
- [ ] Planner actions are finite, use the expected move groups, and manipulate only the selected
      arm.
- [ ] The task oracle agrees with reviewed video, including same-support behavior for next-to,
      color selection, and containment for packing.
- [ ] The one-worker smoke run completes and emitted data passes trajectory validation.
- [ ] A two-worker smoke run completes without pickling or worker-import errors.
- [ ] At least 100 successful pilot episodes and 10 reviewed videos meet the gate.
- [ ] Attempt count, success count, raw yield, failure categories, and output location are logged.

Promote `adapter` to `pilot` only after the missing adapter is implemented and the cell
constructs. Promote `pilot` to `existing` only after the full per-cell checklist passes. A single
successful episode is not enough to change readiness.

### Validation log

Update this table as testing proceeds. Add separate rows for left and right active arms.

| Task | Embodiment | Active arm | Config | Smoke attempts/successes | Validator | Videos reviewed | Readiness decision | Notes/output path |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| _Not run_ | _Not run_ | _N/A_ | _Not run_ | 0/0 | Not run | 0 | Unchanged | Tests and rollouts intentionally deferred during implementation |

## Definition of done

The project is production-ready when every intended matrix cell has a constructible config,
passing integration coverage, reviewed pilot videos, recorded raw-yield metrics, and validated
balanced output. Large-scale generation is deliberately not triggered by repository setup: the
operator must choose episode counts, assets, output storage, and compute allocation explicitly.
