# CPU-Only Multi-Embodiment Tabletop Data Generation Plan

## Objective

Generate reproducible demonstrations for five tabletop task families across the bundled
manipulation-capable embodiments that do not require CUDA:

- `pick`
- `pick_and_place`
- `pick_and_place_next_to`
- `pick_and_place_color`
- `packing`

The CPU production target and launcher contain 40 cells: five tasks by eight embodiment
profiles.

## Scope

The CPU-only rollout covers these built-in embodiment profiles:

1. Franka DROID
2. Mobile Franka
3. Franka CAP
4. RB-Y1
5. Floating RUM
6. Floating Robotiq 2F-85
7. I2RT YAM
8. Bimanual I2RT YAM

RB-Y1M and `RBY1MOpenCloseConfig` are excluded because their CuRobo planner requires a CUDA
environment. The XArm7 tutorial is excluded because its robot assets are supplied externally.

For dual-arm embodiments, the initial atomic-task implementation uses one active arm per run.
Separate left- and right-arm runs should be balanced in the final dataset. Coordinated bimanual
behavior is outside this plan.

## Readiness levels

Every matrix cell carries one of these readiness labels:

- `reference`: established configuration used as the baseline.
- `existing`: the repository already contains a closely matching data-generation path.
- `pilot`: the common interface is implemented, but the combination needs a pilot rollout.

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
- [x] Exclude the RB-Y1M CuRobo path from the CPU-only matrix.

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

Run these gates for every CPU matrix cell before production:

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
2. Floating RUM, Floating Robotiq, Franka CAP, Mobile Franka, and single-arm YAM.
3. RB-Y1 and Bimanual YAM, with balanced left/right runs.

Balance the final dataset by successful trajectories rather than attempted episodes. Keep scene
and object splits disjoint between train, validation, and test. Preserve native move-group-keyed
actions in raw data; any fixed-width cross-embodiment representation should be a downstream
conversion.

## Usage

Set the persistent CPU runtime environment before running any matrix command. `/home/xiangf`
resolves to `/media/16TBNVME/home/xiangf` on the current machine. These paths keep resources,
renderer libraries, model caches, and outputs out of `/tmp`:

```bash
export MLSPACES_RUNTIME_ROOT=/home/xiangf/molmospaces-data
export MLSPACES_ASSETS_DIR="$MLSPACES_RUNTIME_ROOT/assets"
export MLSPACES_CACHE_DIR="$MLSPACES_RUNTIME_ROOT/resource-cache"
export XDG_CACHE_HOME="$MLSPACES_RUNTIME_ROOT/cache/xdg"
export MPLCONFIGDIR="$MLSPACES_RUNTIME_ROOT/cache/matplotlib"
export HF_HOME="$XDG_CACHE_HOME/huggingface"
export TORCH_HOME="$XDG_CACHE_HOME/torch"
export NLTK_DATA=/home/xiangf/nltk_data
export LD_LIBRARY_PATH="$MLSPACES_RUNTIME_ROOT/osmesa/root/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export MUJOCO_GL=osmesa
export PYOPENGL_PLATFORM=osmesa
```

The current persistent runtime occupies about 16 GB. WordNet and WordNet 2022 are installed at
`/home/xiangf/nltk_data`; the code checks these local corpora before attempting a download.

List the complete 40-cell CPU catalog:

```bash
.venv/bin/python scripts/datagen/run_tabletop_matrix.py --list
```

Validate configuration construction for one cell:

```bash
.venv/bin/python scripts/datagen/run_tabletop_matrix.py \
  --task pick_and_place \
  --embodiment franka_droid \
  --validate-only
```

Run a small pilot:

```bash
.venv/bin/python scripts/datagen/run_tabletop_matrix.py \
  --task pick_and_place \
  --embodiment franka_droid \
  --samples-per-house 2 \
  --max-tasks 20 \
  --house-indices 0 1 2 3
```

An unvalidated cell additionally requires `--allow-unvalidated`.

After every CPU cell has passed its pilot gate, select the complete 40-cell matrix:

```bash
.venv/bin/python scripts/datagen/run_tabletop_matrix.py \
  --all --allow-unvalidated --balance-arms
```

The arm-balancing flag creates separate left/right output directories for RB-Y1 and Bimanual
YAM. Keep a bounded `--max-tasks` until storage and throughput have been confirmed.

## Next-agent testing and debugging handoff

### Current state and guardrails

- From 2026-07-14 to 2026-07-15 UTC, the fixed-house seed-0 smoke matrix launched all 40 CPU
  task/embodiment cells. Seven cells saved a successful trajectory, 13 completed with
  `success=False`, and 20 raised a reset/control exception before the pipeline counted an
  episode. See the complete matrix below. These are smoke results, not production-readiness
  results.
- The earlier Franka DROID `pick` reference smoke and the new matrix run both completed with 1/1
  success and 57 saved timesteps for seed 0, house 0.
- The trajectory validator, statistics pass, two-worker check, and manual video review have not
  been run in this session.
- On 2026-07-15, policy completion metadata was removed from robot control dictionaries at the
  shared task boundary, fixing the Floating RUM/Robotiq `KeyError: 'success'`. The affected
  rollout cells still need integration reruns.
- All persistent runtime data is under `/home/xiangf/molmospaces-data`: `assets/`,
  `resource-cache/`, `osmesa/`, `cache/`, and `output/tabletop/`. Do not reintroduce `/tmp` paths.
- `molmo_spaces/renderer/opengl_rendering.py` now distinguishes the actual MuJoCo CGL context
  from Linux OSMesa. Before this fix, every non-EGL context was treated as macOS CGL and the CPU
  run failed while loading `/System/Library/Frameworks/OpenGL.framework/OpenGL`.
- Treat all `pilot` cells as unvalidated, regardless of whether their configuration constructs.
  Do not promote readiness or start production generation until the validation funnel passes.
- Start with one worker, one house, and one attempted episode. Do not use `--all` while debugging.
- The registered catalog contains exactly the 40 CPU cells; RB-Y1M is not registered by this
  launcher.
- RGB observations still require an OpenGL backend. On a machine without a GPU, use an OSMesa
  software-rendering environment; CPU physics working alone is not enough for visual data.
- Use a fresh `--run-name` under the persistent output root while debugging. Stable output paths
  resume by skipping batches that already exist, which can hide whether a code change fixed a
  rollout.
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
- `molmo_spaces/renderer/opengl_rendering.py`: actual-backend detection for CGL versus OSMesa.
- `molmo_spaces/utils/synset_utils.py`: local WordNet checks before fallback downloads.

### Test in this order

1. Check the patch before importing simulation code:

   ```bash
   git status --short
   git diff --check
   ```

2. List the registered CPU catalog without loading simulation assets:

   ```bash
   .venv/bin/python scripts/datagen/run_tabletop_matrix.py --list
   ```

   Expected result: 40 registered rows with stable config names and readiness labels.

3. Run the existing MolmoSpaces data-generation regression tests:

   ```bash
   .venv/bin/pytest -q mlspaces_tests/data_generation/test_datagen_configs.py
   ```

4. Run targeted static checks on the new and materially changed Python files:

   ```bash
   ruff check molmo_spaces/data_generation/config/tabletop_datagen_configs.py \
     scripts/datagen/run_tabletop_matrix.py \
     molmo_spaces/renderer/opengl_rendering.py \
     molmo_spaces/utils/synset_utils.py
   ruff format --check molmo_spaces/data_generation/config/tabletop_datagen_configs.py \
     scripts/datagen/run_tabletop_matrix.py \
     molmo_spaces/renderer/opengl_rendering.py \
     molmo_spaces/utils/synset_utils.py
   ```

5. Construct one reference config, followed by each CPU embodiment. Add `--allow-unvalidated`
   for a `pilot` cell:

   ```bash
   .venv/bin/python scripts/datagen/run_tabletop_matrix.py \
     --task pick --embodiment franka_droid --validate-only

   .venv/bin/python scripts/datagen/run_tabletop_matrix.py \
     --task pick --embodiment mobile_franka --allow-unvalidated --validate-only

   .venv/bin/python scripts/datagen/run_tabletop_matrix.py \
     --task pick --embodiment bimanual_yam --active-gripper right \
     --allow-unvalidated --validate-only
   ```

   Repeat the second pattern for `franka_cap`, `rby1`, `floating_rum`, `floating_robotiq`,
   `i2rt_yam`, and `bimanual_yam`. Exercise both arms of `rby1` and `bimanual_yam`. Then repeat
   across the five tasks. A successful construction is necessary but is not evidence that IK,
   cameras, grasps, or success predicates work in simulation.

6. Run the first simulation smoke test with software rendering, a single process, a fixed seed,
   and a fresh output directory. First apply the persistent environment exports from `Usage`:

   ```bash
   .venv/bin/python scripts/datagen/run_tabletop_matrix.py \
     --task pick \
     --embodiment franka_droid \
     --house-indices 0 \
     --samples-per-house 1 \
     --max-tasks 5 \
     --num-workers 1 \
     --seed 0 \
     --output-root /home/xiangf/molmospaces-data/output/tabletop \
     --run-name first_pass_osmesa
   ```

   Actual result on 2026-07-14: the run selected the polished metal fork, found a feasible grasp,
   executed open/pregrasp/grasp/close/lift, reported task success, and saved 1/1 trajectories.
   The episode took 87.06 seconds; initial one-time resource/index compilation made the complete
   house work item take 333.91 seconds. Warp printed a CUDA-driver warning but selected its CPU
   device and completed successfully.

   Once this passes, test the remaining Franka DROID tasks in this order: `pick_and_place`,
   `pick_and_place_next_to`, `pick_and_place_color`, then `packing`. Next follow the production
   rollout order above. Add `--allow-unvalidated` for every pilot cell.

7. Only after a cell works with `--num-workers 1`, repeat a small run with two workers. This
   specifically checks that dynamically generated configuration classes remain pickle-safe:

   ```bash
   .venv/bin/python scripts/datagen/run_tabletop_matrix.py \
     --task pick \
     --embodiment franka_droid \
     --house-indices 0 1 \
     --samples-per-house 1 \
     --max-tasks 2 \
     --num-workers 2 \
     --output-root /home/xiangf/molmospaces-data/output/tabletop \
     --run-name two_workers
   ```

### Expected artifacts and validation

A launched cell should create the following beneath
`<output-root>/<embodiment>/<task>/<run-name>/`:

- `tabletop_run_manifest.json`, including matrix version, source revision, task, embodiment,
  readiness, active gripper, camera roles, resource versions, and sampling parameters.
- `experiment_config_<timestamp>.pkl`.
- `running_log.log`.
- `house_<id>/trajectories*.h5` and its corresponding camera MP4 files after successful
  trajectories are saved.
- With `--balance-arms`, `active_left/` and `active_right/` directories for dual-arm profiles.

Run structural and video validation in dry-run mode first:

```bash
.venv/bin/python scripts/data/validate_trajectories.py \
  /home/xiangf/molmospaces-data/output/tabletop/franka_droid/pick/first_pass_osmesa \
  --num-workers 1 \
  --dry-run
```

Inspect the available data keys before choosing the statistics keys for a new embodiment, then
run statistics without writing during initial debugging:

```bash
.venv/bin/python scripts/data/view_data.py \
  /home/xiangf/molmospaces-data/output/tabletop/franka_droid/pick/first_pass_osmesa

.venv/bin/python scripts/data/calculate_stats.py \
  /home/xiangf/molmospaces-data/output/tabletop/franka_droid/pick/first_pass_osmesa \
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
| Matrix row is missing, duplicated, or cannot be imported | Generated class registration and module globals in `tabletop_datagen_configs.py` | `--list` shows exactly 40 unique config names |
| Wrong arm moves or sensor labels reference the other arm | `active_gripper_move_group_id`, `active_ik_move_group_ids`, robot-view setter, and profile `active_gripper_ids` | Left/right smoke runs move only the selected arm and manifests record it |
| Target sampling repeatedly fails | Per-profile reach, safety radius, vertical placement, table bounds, and active TCP pose | At least 20 sampled targets are in bounds and reachable |
| IK fails or returns NaNs | Active IK groups, TCP transform, joint limits, grasp pose, and batch-IK support flag | Finite actions and successful IK for sampled approach/grasp/place poses |
| Object is reachable but never grasped | Grasp library compatibility, gripper TCP, finger geometry, collision masks, and close command | Stable lift in reviewed video; do not weaken the success oracle to compensate |
| Next-to episodes execute as ordinary place | Next-to planner adapter and same-support/surface-gap success checks | Placed object and reference object share support and satisfy the configured gap |
| Color task chooses the wrong receptacle | Color task sampler metadata, language fields, and receptacle selection | Manifest/task data and video agree on the requested color |
| Packing cannot sample or close around objects | Box assets, dimensions, flap state, and `packing_task_sampler.py` | Objects finish inside the intended box and oracle success matches video |
| A camera is missing, black, or does not see the target | Profile `camera_config_factory`, camera-role mapping, renderer backend, and extrinsics | Valid MP4 frames and target visibility in reviewed episodes |
| CPU smoke run cannot create an OpenGL context | OSMesa system libraries, `MUJOCO_GL=osmesa`, and `PYOPENGL_PLATFORM=osmesa` | The standalone 64x64 MuJoCo software-rendering probe succeeds before loading project assets |
| Single worker passes but multiprocessing fails | Pickling of generated config classes, lazy policy builders, and worker imports | The two-worker smoke run produces valid HDF5 and MP4 output |
| Rerun exits without exercising changed code | Existing `trajectories*.h5` resume behavior | Reproduce with a fresh `--run-name` beneath the persistent output root |

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

Promote `pilot` to `existing` only after the full per-cell checklist passes. A single successful
episode is not enough to change readiness.

### Fixed-house 40-cell CPU smoke result (2026-07-14/15 UTC)

The launcher ran one bounded attempt for every combination of five tasks and eight CPU
embodiments. It used house 0, seed 0, one worker, `samples_per_house=1`, and `max_tasks=1`:

```bash
.venv/bin/python scripts/datagen/run_tabletop_matrix.py \
  --task pick pick_and_place pick_and_place_next_to pick_and_place_color packing \
  --embodiment franka_droid mobile_franka franka_cap rby1 \
    floating_rum floating_robotiq i2rt_yam bimanual_yam \
  --allow-unvalidated \
  --house-indices 0 \
  --samples-per-house 1 \
  --max-tasks 1 \
  --num-workers 1 \
  --seed 0 \
  --output-root /home/xiangf/molmospaces-data/output/tabletop \
  --run-name cpu_matrix_40_house0_seed0_20260714
```

The process completed in about 51 minutes. It created 40 manifests, 40 pickled configs, seven
trajectory HDF5 files, and 14 MP4 files (about 15 MB total). The output root for any cell is:

```text
/home/xiangf/molmospaces-data/output/tabletop/<embodiment>/<task>/cpu_matrix_40_house0_seed0_20260714
```

This was a 40-cell attempt, not 40 completed episodes. Twenty cells reached a counted rollout
result: seven were successful and 13 returned `success=False`. The other 20 report `0/0` because
an exception occurred during policy reset or control before the pipeline counted the rollout.

Legend: `pass` saved HDF5 and video data; `TCP` exhausted the default TCP tracking retries;
`oracle` executed the trajectory but returned `success=False`; `IK-*` names the pose whose IK
failed; and `action-key` is `KeyError: 'success'` in floating-gripper control after planner
failure.

| Task | Franka DROID | Mobile Franka | Franka CAP | RB-Y1 | Floating RUM | Floating Robotiq | I2RT YAM | Bimanual YAM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pick` | 1/1 pass | 0/1 TCP | 0/1 TCP | 0/1 TCP | 0/0 action-key | 0/0 action-key | 0/0 IK-pregrasp | 0/0 IK-pregrasp |
| `pick_and_place` | 0/0 IK-preplace | 0/1 TCP | 0/0 IK-preplace | 0/1 TCP | 1/1 pass | 1/1 pass | 0/0 IK-lift | 0/0 IK-pregrasp |
| `pick_and_place_next_to` | 0/1 oracle | 0/1 TCP | 0/0 IK-grasp | 0/1 TCP | 1/1 pass | 0/1 oracle | 0/0 IK-lift | 0/0 IK-pregrasp |
| `pick_and_place_color` | 0/0 IK-preplace | 0/1 TCP | 0/0 IK-pregrasp | 0/1 TCP | 0/0 action-key | 1/1 pass | 0/0 IK-pregrasp | 0/0 IK-pregrasp |
| `packing` | 0/0 IK-grasp | 0/1 TCP | 0/0 IK-pregrasp | 0/1 TCP | 1/1 pass | 1/1 pass | 0/0 IK-pregrasp | 0/0 IK-pregrasp |

The exception totals were: ten pregrasp IK failures, three preplace IK failures, two grasp IK
failures, two lift IK failures, and three floating-gripper `action-key` failures. All 13 counted
failures completed with `success=False`; 11 of those exhausted TCP retries, while the Franka
DROID and Floating Robotiq next-to cells completed their motions but failed the task oracle.

The seven saved trajectories contain:

| Task | Embodiment | Timesteps |
| --- | --- | ---: |
| `pick` | Franka DROID | 57 |
| `pick_and_place` | Floating RUM | 267 |
| `pick_and_place` | Floating Robotiq | 291 |
| `pick_and_place_next_to` | Floating RUM | 344 |
| `pick_and_place_color` | Floating Robotiq | 307 |
| `packing` | Floating RUM | 288 |
| `packing` | Floating Robotiq | 300 |

No trajectory validator, statistics pass, or video review has been performed on these outputs.
Also note a logging issue: handlers accumulate when 40 runners execute in one process, causing
later console messages to repeat. The first cell's `running_log.log` contains the chronological
result stream for all 40 cells and is the most useful aggregate debug log.

The three `action-key` entries above describe the original matrix run. They were fixed afterward
by stripping policy-only `done` and `success` fields before robot control. Rerun the affected
cells to measure their underlying planner success after the exception is removed.

### Validation log

Update this table as testing proceeds. Add separate rows for left and right active arms.

| Task | Embodiment | Active arm | Config | Smoke attempts/successes | Validator | Videos reviewed | Readiness decision | Notes/output path |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pick` | Franka DROID | `gripper` | Pass | 1/1 | Not run | 0 | Keep `reference` | Seed 0, house 0, OSMesa CPU, 57 timesteps; `/home/xiangf/molmospaces-data/output/tabletop/franka_droid/pick/first_pass_osmesa` |
| `pick` | Franka DROID | `gripper` | Pass | 1/1 | Not run | 0 | Keep `reference` | Matrix run, 57 timesteps; `franka_droid/pick/cpu_matrix_40_house0_seed0_20260714` |
| `pick_and_place` | Floating RUM | `gripper` | Pass | 1/1 | Not run | 0 | Keep `pilot` | Matrix run, 267 timesteps; `floating_rum/pick_and_place/cpu_matrix_40_house0_seed0_20260714` |
| `pick_and_place` | Floating Robotiq | `gripper` | Pass | 1/1 | Not run | 0 | Keep `pilot` | Matrix run, 291 timesteps; `floating_robotiq/pick_and_place/cpu_matrix_40_house0_seed0_20260714` |
| `pick_and_place_next_to` | Floating RUM | `gripper` | Pass | 1/1 | Not run | 0 | Keep `pilot` | Matrix run, 344 timesteps; `floating_rum/pick_and_place_next_to/cpu_matrix_40_house0_seed0_20260714` |
| `pick_and_place_color` | Floating Robotiq | `gripper` | Pass | 1/1 | Not run | 0 | Keep `pilot` | Matrix run, 307 timesteps; `floating_robotiq/pick_and_place_color/cpu_matrix_40_house0_seed0_20260714` |
| `packing` | Floating RUM | `gripper` | Pass | 1/1 | Not run | 0 | Keep `pilot` | Matrix run, 288 timesteps; `floating_rum/packing/cpu_matrix_40_house0_seed0_20260714` |
| `packing` | Floating Robotiq | `gripper` | Pass | 1/1 | Not run | 0 | Keep `pilot` | Matrix run, 300 timesteps; `floating_robotiq/packing/cpu_matrix_40_house0_seed0_20260714` |

## Definition of done

The project is production-ready when every intended matrix cell has a constructible config,
passing integration coverage, reviewed pilot videos, recorded raw-yield metrics, and validated
balanced output. Large-scale generation is deliberately not triggered by repository setup: the
operator must choose episode counts, assets, output storage, and compute allocation explicitly.
