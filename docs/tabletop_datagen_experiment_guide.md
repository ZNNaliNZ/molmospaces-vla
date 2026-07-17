# Full Tabletop Data-Generation Run

## Command

This is one valid run using every compatible generation parameter. It selects all five tasks,
all eight CPU embodiments, both arms of dual-arm robots, four houses, and one requested successful
trajectory per house.

```bash
cd /home/xiangf/molmospaces

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
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"

.venv/bin/python scripts/datagen/run_tabletop_matrix.py \
  --all \
  --allow-unvalidated \
  --balance-arms \
  --scene-dataset procthor-10k \
  --data-split train \
  --seed 0 \
  --num-workers 1 \
  --samples-per-house 1 \
  --max-tasks 24 \
  --house-indices 0 1 2 3 \
  --output-root /home/xiangf/molmospaces-data/output/tabletop \
  --run-name all_tasks_all_embodiments_train_seed0
```

## Parameter explanations

| Parameter | Explanation |
| --- | --- |
| `--all` | Selects all 40 task/embodiment cells: five tasks multiplied by eight embodiments. |
| `--allow-unvalidated` | Allows cells currently marked `pilot` to run. It does not guarantee that those cells will succeed. |
| `--balance-arms` | Runs both left and right arms for RB-Y1 and Bimanual YAM. This expands the command from 40 cells to 50 arm-specific runs. Remove it to use the default left arm and run only 40 cells. |
| `--scene-dataset procthor-10k` | Selects the ProcTHOR-10K scene dataset. This is where the input house scenes come from. |
| `--data-split train` | Uses the training split of the selected scene dataset. Accepted values are `train`, `val`, and `test`. |
| `--seed 0` | Seeds Python, NumPy, and Torch task-sampling randomness. It influences object selection, object and robot placement, initial-state noise, grasps, and cameras. One worker gives the strongest practical repeatability. |
| `--num-workers 1` | Uses one CPU worker process. This controls CPU parallelism, not GPU count. Increase it only after single-worker runs work correctly. |
| `--samples-per-house 1` | Requests one successful saved trajectory for each house in every task/embodiment/arm run. Failed attempts normally are not saved to the main HDF5. |
| `--max-tasks 24` | Gives each worker a maximum of 24 task-sampling calls for each task/embodiment/arm run. With four houses and one requested success per house, this allows up to six sampling calls per target. |
| `--house-indices 0 1 2 3` | Uses exactly houses 0, 1, 2, and 3. The house set is fixed rather than randomly selected. |
| `--output-root .../output/tabletop` | Sets the generated-data root. Each run is written below `<output-root>/<embodiment>/<task>/`. |
| `--run-name all_tasks_all_embodiments_train_seed0` | Names this experiment beneath every selected task directory. Use a new name for a fresh run; reusing the name resumes and skips existing HDF5 batches. |

## Other available CLI parameters

These parameters are not included above because they replace or conflict with options in the full
run:

| Parameter | Explanation |
| --- | --- |
| `--task TASK ...` | Selects specific tasks. Use it together with `--embodiment` instead of `--all`. Choices are `pick`, `pick_and_place`, `pick_and_place_next_to`, `pick_and_place_color`, and `packing`. |
| `--embodiment ROBOT ...` | Selects specific embodiments. Use it together with `--task` instead of `--all`. Choices are `franka_droid`, `mobile_franka`, `franka_cap`, `rby1`, `floating_rum`, `floating_robotiq`, `i2rt_yam`, and `bimanual_yam`. |
| `--active-gripper left` or `right` | Selects one arm for one embodiment. It cannot be combined with `--balance-arms`. |
| `--viewer` | Opens the passive viewer. It is allowed only when exactly one arm-specific cell is selected and is not suitable for the full matrix command. |
| `--validate-only` | Constructs selected configurations without generating trajectories. |
| `--list` | Prints all supported matrix cells and exits without running an experiment. |

The output for balanced dual-arm cells is:

```text
<output-root>/<embodiment>/<task>/active_left/<run-name>/
<output-root>/<embodiment>/<task>/active_right/<run-name>/
```

Single-arm outputs omit the `active_left` or `active_right` directory.
