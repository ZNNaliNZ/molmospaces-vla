"""Multi-embodiment tabletop data-generation configuration matrix.

This module keeps task semantics and embodiment-specific integration details orthogonal. Every
matrix cell is exported as a stable module-level config class and registered with the standard
data-generation registry, while :func:`build_tabletop_config` supports programmatic overrides.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from molmo_spaces.configs.abstract_exp_config import MlSpacesExpConfig
from molmo_spaces.configs.camera_configs import (
    BimanualYamCameraSystem,
    CameraSystemConfig,
    FrankaDroidCameraSystem,
    FrankaRandomizedD405D455CameraSystem,
    FrankaRobotiq2f85CameraSystem,
    I2rtYamCameraSystem,
    RBY1GoProD455CameraSystem,
    RandomizedExocentricCameraConfig,
)
from molmo_spaces.configs.policy_configs import (
    BasePolicyConfig,
    PickAndPlaceColorPlannerPolicyConfig,
    PickAndPlaceNextToPlannerPolicyConfig,
    PickAndPlacePlannerPolicyConfig,
    PickPlannerPolicyConfig,
)
from molmo_spaces.configs.robot_configs import (
    BaseRobotConfig,
    BimanualYamRobotConfig,
    FloatingRobotiq2f85RobotConfig,
    FloatingRUMRobotConfig,
    FrankaCAPRobotConfig,
    FrankaRobotConfig,
    I2rtYamRobotConfig,
    MobileFrankaRobotConfig,
    RBY1Config,
)
from molmo_spaces.configs.task_configs import (
    AllTaskConfigs,
    PackingTaskConfig,
    PickAndPlaceColorTaskConfig,
    PickAndPlaceNextToTaskConfig,
    PickAndPlaceTaskConfig,
    PickTaskConfig,
)
from molmo_spaces.configs.task_sampler_configs import (
    BaseMujocoTaskSamplerConfig,
    PackingTaskSamplerConfig,
    PickAndPlaceColorTaskSamplerConfig,
    PickAndPlaceNextToTaskSamplerConfig,
    PickAndPlaceTaskSamplerConfig,
    PickTaskSamplerConfig,
)
from molmo_spaces.data_generation.config_registry import register_config
from molmo_spaces.molmo_spaces_constants import (
    ASSETS_DIR,
    DATA_TYPE_TO_SOURCE_TO_VERSION,
)
from molmo_spaces.tasks.packing_task import PackingTask
from molmo_spaces.tasks.packing_task_sampler import PackingTaskSampler
from molmo_spaces.tasks.pick_and_place_color_task import PickAndPlaceColorTask
from molmo_spaces.tasks.pick_and_place_color_task_sampler import PickAndPlaceColorTaskSampler
from molmo_spaces.tasks.pick_and_place_next_to_task import PickAndPlaceNextToTask
from molmo_spaces.tasks.pick_and_place_next_to_task_sampler import PickAndPlaceNextToTaskSampler
from molmo_spaces.tasks.pick_and_place_task import PickAndPlaceTask
from molmo_spaces.tasks.pick_and_place_task_sampler import PickAndPlaceTaskSampler
from molmo_spaces.tasks.pick_task import PickTask
from molmo_spaces.tasks.pick_task_sampler import PickTaskSampler
from molmo_spaces.utils.constants.object_constants import PICK_AND_PLACE_OBJECTS

TABLETOP_MATRIX_VERSION = "1"
TABLETOP_SUPPORT_TYPES = (
    "CoffeeTable",
    "CounterTop",
    "Desk",
    "DiningTable",
    "Dresser",
    "SideTable",
    "TVStand",
)


class TabletopReadiness(StrEnum):
    """Runtime confidence for a task/embodiment matrix cell."""

    REFERENCE = "reference"
    EXISTING = "existing"
    PILOT = "pilot"


@dataclass(frozen=True)
class TabletopTaskProfile:
    key: str
    class_suffix: str
    task_config_factory: Callable[[], AllTaskConfigs]
    sampler_config_factory: Callable[[], BaseMujocoTaskSamplerConfig]
    policy_config_factory: Callable[[], BasePolicyConfig]


@dataclass(frozen=True)
class TabletopEmbodimentProfile:
    key: str
    class_prefix: str
    robot_config_factory: Callable[[], BaseRobotConfig]
    camera_config_factory: Callable[[], CameraSystemConfig]
    active_gripper_ids: tuple[str, ...]
    ik_move_groups_by_gripper: Mapping[str, tuple[str, ...]]
    sampler_overrides: Mapping[str, Any]
    readiness: Mapping[str, TabletopReadiness]
    camera_roles: Mapping[str, str] | None = None
    supports_parallel_ik: bool = True
    policy_dt_ms: float = 66.0
    ctrl_dt_ms: float = 2.0
    sim_dt_ms: float = 2.0
    notes: str = ""


@dataclass(frozen=True)
class TabletopCombination:
    task: TabletopTaskProfile
    embodiment: TabletopEmbodimentProfile

    @property
    def config_name(self) -> str:
        return f"{self.embodiment.class_prefix}{self.task.class_suffix}TabletopDataGenConfig"

    @property
    def readiness(self) -> TabletopReadiness:
        return self.embodiment.readiness.get(self.task.key, TabletopReadiness.PILOT)


def _pick_task_config() -> PickTaskConfig:
    return PickTaskConfig(task_cls=PickTask)


def _pick_sampler_config() -> PickTaskSamplerConfig:
    return PickTaskSamplerConfig(task_sampler_class=PickTaskSampler)


def _pick_and_place_task_config() -> PickAndPlaceTaskConfig:
    return PickAndPlaceTaskConfig(task_cls=PickAndPlaceTask)


def _pick_and_place_sampler_config() -> PickAndPlaceTaskSamplerConfig:
    return PickAndPlaceTaskSamplerConfig(
        task_sampler_class=PickAndPlaceTaskSampler,
        pickup_types=list(PICK_AND_PLACE_OBJECTS),
    )


def _next_to_task_config() -> PickAndPlaceNextToTaskConfig:
    return PickAndPlaceNextToTaskConfig(task_cls=PickAndPlaceNextToTask)


def _next_to_sampler_config() -> PickAndPlaceNextToTaskSamplerConfig:
    return PickAndPlaceNextToTaskSamplerConfig(
        task_sampler_class=PickAndPlaceNextToTaskSampler,
        pickup_types=list(PICK_AND_PLACE_OBJECTS),
    )


def _color_task_config() -> PickAndPlaceColorTaskConfig:
    return PickAndPlaceColorTaskConfig(task_cls=PickAndPlaceColorTask)


def _color_sampler_config() -> PickAndPlaceColorTaskSamplerConfig:
    return PickAndPlaceColorTaskSamplerConfig(
        task_sampler_class=PickAndPlaceColorTaskSampler,
        pickup_types=list(PICK_AND_PLACE_OBJECTS),
    )


def _packing_task_config() -> PackingTaskConfig:
    return PackingTaskConfig(task_cls=PackingTask)


def _packing_sampler_config() -> PackingTaskSamplerConfig:
    return PackingTaskSamplerConfig(
        task_sampler_class=PackingTaskSampler,
        pickup_types=list(PICK_AND_PLACE_OBJECTS),
    )


TABLETOP_TASK_PROFILES: dict[str, TabletopTaskProfile] = {
    "pick": TabletopTaskProfile(
        key="pick",
        class_suffix="Pick",
        task_config_factory=_pick_task_config,
        sampler_config_factory=_pick_sampler_config,
        policy_config_factory=PickPlannerPolicyConfig,
    ),
    "pick_and_place": TabletopTaskProfile(
        key="pick_and_place",
        class_suffix="PickAndPlace",
        task_config_factory=_pick_and_place_task_config,
        sampler_config_factory=_pick_and_place_sampler_config,
        policy_config_factory=PickAndPlacePlannerPolicyConfig,
    ),
    "pick_and_place_next_to": TabletopTaskProfile(
        key="pick_and_place_next_to",
        class_suffix="PickAndPlaceNextTo",
        task_config_factory=_next_to_task_config,
        sampler_config_factory=_next_to_sampler_config,
        policy_config_factory=PickAndPlaceNextToPlannerPolicyConfig,
    ),
    "pick_and_place_color": TabletopTaskProfile(
        key="pick_and_place_color",
        class_suffix="PickAndPlaceColor",
        task_config_factory=_color_task_config,
        sampler_config_factory=_color_sampler_config,
        policy_config_factory=PickAndPlaceColorPlannerPolicyConfig,
    ),
    "packing": TabletopTaskProfile(
        key="packing",
        class_suffix="Packing",
        task_config_factory=_packing_task_config,
        sampler_config_factory=_packing_sampler_config,
        policy_config_factory=PickAndPlacePlannerPolicyConfig,
    ),
}


def _floating_gripper_camera_system() -> CameraSystemConfig:
    """Use stable camera aliases without assuming a wrist camera exists in the MJCF."""
    common_visibility = {"__task_objects__": 0.0001, "__gripper__": 0.0001}
    return CameraSystemConfig(
        img_resolution=(640, 480),
        cameras=[
            RandomizedExocentricCameraConfig(
                name="exo_camera_1",
                distance_range=(0.35, 0.9),
                height_range=(0.35, 0.9),
                azimuth_range=(0.0, 6.283185307179586),
                fov_range=(50.0, 90.0),
                lookat_noise_range=(-0.05, 0.05),
                visibility_constraints=common_visibility,
                allow_relaxed_constraints=True,
            ),
            RandomizedExocentricCameraConfig(
                name="exo_camera_2",
                distance_range=(0.35, 0.9),
                height_range=(0.35, 0.9),
                azimuth_range=(0.0, 6.283185307179586),
                fov_range=(50.0, 90.0),
                lookat_noise_range=(-0.05, 0.05),
                visibility_constraints=common_visibility,
                allow_relaxed_constraints=True,
            ),
        ],
    )


_ALL_REFERENCE = {
    "pick": TabletopReadiness.REFERENCE,
    "pick_and_place": TabletopReadiness.REFERENCE,
    "pick_and_place_next_to": TabletopReadiness.REFERENCE,
    "pick_and_place_color": TabletopReadiness.REFERENCE,
    "packing": TabletopReadiness.PILOT,
}
_ALL_PILOT = {task: TabletopReadiness.PILOT for task in TABLETOP_TASK_PROFILES}


TABLETOP_EMBODIMENT_PROFILES: dict[str, TabletopEmbodimentProfile] = {
    "franka_droid": TabletopEmbodimentProfile(
        key="franka_droid",
        class_prefix="FrankaDroid",
        robot_config_factory=FrankaRobotConfig,
        camera_config_factory=FrankaDroidCameraSystem,
        active_gripper_ids=("gripper",),
        ik_move_groups_by_gripper={"gripper": ("arm",)},
        sampler_overrides={},
        readiness=_ALL_REFERENCE,
        camera_roles={"wrist": "wrist_camera", "exo": "exo_camera_1"},
        notes="Reference tabletop embodiment.",
    ),
    "mobile_franka": TabletopEmbodimentProfile(
        key="mobile_franka",
        class_prefix="MobileFranka",
        robot_config_factory=MobileFrankaRobotConfig,
        camera_config_factory=FrankaRandomizedD405D455CameraSystem,
        active_gripper_ids=("gripper",),
        ik_move_groups_by_gripper={"gripper": ("base", "arm")},
        sampler_overrides={"robot_safety_radius": 0.35},
        readiness=_ALL_PILOT,
        camera_roles={"wrist": "wrist_camera", "exo": "exo_camera_1"},
        notes="Holonomic base participates in generic IK.",
    ),
    "franka_cap": TabletopEmbodimentProfile(
        key="franka_cap",
        class_prefix="FrankaCAP",
        robot_config_factory=FrankaCAPRobotConfig,
        camera_config_factory=FrankaDroidCameraSystem,
        active_gripper_ids=("gripper",),
        ik_move_groups_by_gripper={"gripper": ("arm",)},
        sampler_overrides={},
        readiness=_ALL_PILOT,
        camera_roles={"wrist": "wrist_camera", "exo": "exo_camera_1"},
        notes="Requires CAP TCP, gripper-width, and camera calibration pilot.",
    ),
    "rby1": TabletopEmbodimentProfile(
        key="rby1",
        class_prefix="RBY1",
        robot_config_factory=RBY1Config,
        camera_config_factory=RBY1GoProD455CameraSystem,
        active_gripper_ids=("left_gripper", "right_gripper"),
        ik_move_groups_by_gripper={
            "left_gripper": ("base", "torso", "left_arm"),
            "right_gripper": ("base", "torso", "right_arm"),
        },
        sampler_overrides={
            "robot_safety_radius": 0.35,
            "max_robot_to_obj_dist": 0.5,
            "max_robot_to_place_receptacle_dist": 0.5,
            "object_placement_radius_range": (0.1, 0.5),
        },
        readiness=_ALL_PILOT,
        camera_roles={
            "wrist_left": "wrist_camera_l",
            "wrist_right": "wrist_camera_r",
            "exo": "head_camera",
        },
        supports_parallel_ik=False,
        policy_dt_ms=100.0,
        ctrl_dt_ms=20.0,
        sim_dt_ms=4.0,
        notes="Sequential MuJoCo IK fallback; select one arm explicitly.",
    ),
    "floating_rum": TabletopEmbodimentProfile(
        key="floating_rum",
        class_prefix="FloatingRUM",
        robot_config_factory=FloatingRUMRobotConfig,
        camera_config_factory=_floating_gripper_camera_system,
        active_gripper_ids=("gripper",),
        ik_move_groups_by_gripper={"gripper": ("base",)},
        sampler_overrides={
            "robot_object_z_offset": 0.0,
            "robot_object_z_offset_random_min": 0.0,
            "robot_object_z_offset_random_max": 0.0,
            "base_pose_sampling_radius_range": (0.0, 0.8),
            "robot_safety_radius": 0.2,
        },
        readiness={
            "pick": TabletopReadiness.EXISTING,
            "pick_and_place": TabletopReadiness.PILOT,
            "pick_and_place_next_to": TabletopReadiness.PILOT,
            "pick_and_place_color": TabletopReadiness.PILOT,
            "packing": TabletopReadiness.PILOT,
        },
        camera_roles={"exo": "exo_camera_1", "exo_secondary": "exo_camera_2"},
        notes="Floating 6-DoF base; exocentric cameras avoid MJCF wrist assumptions.",
    ),
    "floating_robotiq": TabletopEmbodimentProfile(
        key="floating_robotiq",
        class_prefix="FloatingRobotiq",
        robot_config_factory=FloatingRobotiq2f85RobotConfig,
        camera_config_factory=FrankaRobotiq2f85CameraSystem,
        active_gripper_ids=("gripper",),
        ik_move_groups_by_gripper={"gripper": ("base",)},
        sampler_overrides={
            "robot_object_z_offset": 0.0,
            "robot_object_z_offset_random_min": 0.0,
            "robot_object_z_offset_random_max": 0.0,
            "base_pose_sampling_radius_range": (0.0, 0.8),
            "robot_safety_radius": 0.2,
        },
        readiness=_ALL_PILOT,
        camera_roles={"wrist": "wrist_camera", "exo": "exo_camera_1"},
        notes="Floating Robotiq integration requires a full pilot.",
    ),
    "i2rt_yam": TabletopEmbodimentProfile(
        key="i2rt_yam",
        class_prefix="I2rtYam",
        robot_config_factory=I2rtYamRobotConfig,
        camera_config_factory=I2rtYamCameraSystem,
        active_gripper_ids=("gripper",),
        ik_move_groups_by_gripper={"gripper": ("arm",)},
        sampler_overrides={"robot_object_z_offset": -0.7},
        readiness=_ALL_PILOT,
        camera_roles={"wrist": "wrist_camera", "exo": "exo_camera_1"},
        notes="Single-arm YAM generic MuJoCo IK path.",
    ),
    "bimanual_yam": TabletopEmbodimentProfile(
        key="bimanual_yam",
        class_prefix="BimanualYam",
        robot_config_factory=BimanualYamRobotConfig,
        camera_config_factory=BimanualYamCameraSystem,
        active_gripper_ids=("left_gripper", "right_gripper"),
        ik_move_groups_by_gripper={
            "left_gripper": ("left_arm",),
            "right_gripper": ("right_arm",),
        },
        sampler_overrides={"robot_object_z_offset": -0.7},
        readiness=_ALL_PILOT,
        camera_roles={
            "wrist_left": "left_wrist_camera",
            "wrist_right": "right_wrist_camera",
            "exo": "exo_camera",
        },
        supports_parallel_ik=False,
        notes="Atomic tasks use one selected arm per run.",
    ),
}


class TabletopDataGenConfig(MlSpacesExpConfig):
    """Broadly typed experiment config used by every tabletop matrix cell."""

    tabletop_matrix_version: str = TABLETOP_MATRIX_VERSION
    tabletop_task: str
    tabletop_embodiment: str
    tabletop_readiness: str
    tabletop_source_revision: str | None = None
    tabletop_resource_versions: dict[str, str] = {}
    tabletop_camera_roles: dict[str, str] = {}

    num_envs: int = 1
    num_workers: int = 1
    use_passive_viewer: bool = False
    viewer_cam_dict: dict = {
        "distance": 3.0,
        "azimuth": 45.0,
        "elevation": -30.0,
        "lookat": [0.0, 0.0, 0.8],
    }
    policy_dt_ms: float = 66.0
    ctrl_dt_ms: float = 2.0
    sim_dt_ms: float = 2.0
    task_horizon: int = 500
    task_type: str
    scene_dataset: str = "procthor-10k"
    data_split: str = "train"

    robot_config: BaseRobotConfig
    camera_config: CameraSystemConfig
    task_sampler_config: BaseMujocoTaskSamplerConfig
    task_config: AllTaskConfigs
    policy_config: BasePolicyConfig
    output_dir: Path

    filter_for_successful_trajectories: bool = True
    profile: bool = False
    use_wandb: bool = False
    wandb_project: str | None = "molmo-spaces-tabletop-datagen"

    @property
    def tag(self) -> str:
        return f"tabletop_{self.tabletop_embodiment}_{self.tabletop_task}"


def _normalize_active_gripper(
    profile: TabletopEmbodimentProfile, active_gripper: str | None
) -> str:
    if active_gripper in {"left", "right"}:
        active_gripper = f"{active_gripper}_gripper"
    selected = active_gripper or profile.active_gripper_ids[0]
    if selected not in profile.active_gripper_ids:
        raise ValueError(
            f"Active gripper '{selected}' is invalid for {profile.key}; "
            f"choose one of {profile.active_gripper_ids}"
        )
    return selected


def _apply_sampler_overrides(
    sampler_config: BaseMujocoTaskSamplerConfig,
    overrides: Mapping[str, Any],
) -> None:
    for key, value in overrides.items():
        if hasattr(sampler_config, key):
            setattr(sampler_config, key, value)


def _resource_versions(robot_name: str | None, scene_dataset: str, data_split: str) -> dict[str, str]:
    versions: dict[str, str] = {}
    robot_versions = DATA_TYPE_TO_SOURCE_TO_VERSION.get("robots", {})
    if robot_name in robot_versions:
        versions[f"robots/{robot_name}"] = robot_versions[robot_name]

    scene_versions = DATA_TYPE_TO_SOURCE_TO_VERSION.get("scenes", {})
    scene_key = f"{scene_dataset}-{data_split}"
    if scene_key in scene_versions:
        versions[f"scenes/{scene_key}"] = scene_versions[scene_key]
    elif scene_dataset in scene_versions:
        versions[f"scenes/{scene_dataset}"] = scene_versions[scene_dataset]

    for data_type, source in (("objects", "thor"), ("grasps", "droid")):
        version = DATA_TYPE_TO_SOURCE_TO_VERSION.get(data_type, {}).get(source)
        if version is not None:
            versions[f"{data_type}/{source}"] = version
    return versions


def _build_tabletop_config_data(
    task: str,
    embodiment: str,
    *,
    active_gripper: str | None = None,
    scene_dataset: str = "procthor-10k",
    data_split: str = "train",
    seed: int | None = None,
    output_dir: Path | None = None,
    num_workers: int = 1,
    samples_per_house: int = 20,
    max_tasks: int | float = float("inf"),
    house_inds: list[int] | None = None,
    use_passive_viewer: bool = False,
) -> dict[str, Any]:
    try:
        task_profile = TABLETOP_TASK_PROFILES[task]
    except KeyError as error:
        raise ValueError(f"Unknown tabletop task '{task}'") from error
    try:
        embodiment_profile = TABLETOP_EMBODIMENT_PROFILES[embodiment]
    except KeyError as error:
        raise ValueError(f"Unknown tabletop embodiment '{embodiment}'") from error

    selected_gripper = _normalize_active_gripper(embodiment_profile, active_gripper)
    robot_config = embodiment_profile.robot_config_factory()
    robot_config.active_gripper_move_group_id = selected_gripper
    robot_config.active_ik_move_group_ids = list(
        embodiment_profile.ik_move_groups_by_gripper[selected_gripper]
    )

    sampler_config = task_profile.sampler_config_factory()
    sampler_config.dataset_name = scene_dataset
    sampler_config.samples_per_house = samples_per_house
    sampler_config.max_tasks = max_tasks
    if hasattr(sampler_config, "receptacle_types"):
        sampler_config.receptacle_types = list(TABLETOP_SUPPORT_TYPES)
    if house_inds is not None:
        sampler_config.house_inds = house_inds
    _apply_sampler_overrides(sampler_config, embodiment_profile.sampler_overrides)

    policy_config = task_profile.policy_config_factory()
    if not embodiment_profile.supports_parallel_ik and hasattr(
        policy_config, "filter_feasible_grasps"
    ):
        policy_config.filter_feasible_grasps = False

    combination = TabletopCombination(task_profile, embodiment_profile)
    resolved_output_dir = output_dir or (
        ASSETS_DIR
        / "experiment_output"
        / "datagen"
        / "tabletop"
        / embodiment
        / task
    )
    return {
        "tabletop_task": task,
        "tabletop_embodiment": embodiment,
        "tabletop_readiness": combination.readiness.value,
        "tabletop_resource_versions": _resource_versions(
            robot_config.name, scene_dataset, data_split
        ),
        "tabletop_camera_roles": dict(embodiment_profile.camera_roles or {}),
        "task_type": task,
        "scene_dataset": scene_dataset,
        "data_split": data_split,
        "seed": seed,
        "num_workers": num_workers,
        "use_passive_viewer": use_passive_viewer,
        "policy_dt_ms": embodiment_profile.policy_dt_ms,
        "ctrl_dt_ms": embodiment_profile.ctrl_dt_ms,
        "sim_dt_ms": embodiment_profile.sim_dt_ms,
        "robot_config": robot_config,
        "camera_config": embodiment_profile.camera_config_factory(),
        "task_sampler_config": sampler_config,
        "task_config": task_profile.task_config_factory(),
        "policy_config": policy_config,
        "output_dir": resolved_output_dir,
    }


def build_tabletop_config(
    task: str,
    embodiment: str,
    **overrides: Any,
) -> TabletopDataGenConfig:
    """Construct one tabletop matrix config with optional runtime overrides."""
    return TabletopDataGenConfig(
        **_build_tabletop_config_data(task, embodiment, **overrides)
    )


def list_tabletop_combinations() -> list[TabletopCombination]:
    """Return all matrix cells in stable task-major order."""
    return [
        TabletopCombination(task_profile, embodiment_profile)
        for task_profile in TABLETOP_TASK_PROFILES.values()
        for embodiment_profile in TABLETOP_EMBODIMENT_PROFILES.values()
    ]


def _register_matrix_config(combination: TabletopCombination) -> None:
    class_name = combination.config_name
    task_key = combination.task.key
    embodiment_key = combination.embodiment.key

    def __init__(self, **kwargs: Any) -> None:
        data = _build_tabletop_config_data(task_key, embodiment_key)
        data.update(kwargs)
        TabletopDataGenConfig.__init__(self, **data)

    generated_cls = type(
        class_name,
        (TabletopDataGenConfig,),
        {
            "__module__": __name__,
            "__qualname__": class_name,
            "__doc__": (
                f"Tabletop config for {combination.task.key} on "
                f"{combination.embodiment.key}."
            ),
            "__init__": __init__,
        },
    )
    globals()[class_name] = generated_cls
    register_config(class_name)(generated_cls)


for _combination in list_tabletop_combinations():
    _register_matrix_config(_combination)
