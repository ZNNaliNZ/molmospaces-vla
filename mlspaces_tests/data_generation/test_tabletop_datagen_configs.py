"""Regression coverage for the tabletop configuration matrix.

These tests intentionally stop at configuration construction. Simulation integration belongs to
the pilot gates documented in ``docs/tabletop_datagen_plan.md``.
"""

from molmo_spaces.data_generation.config.tabletop_datagen_configs import (
    TABLETOP_CONFIG_CLASSES,
    TABLETOP_EMBODIMENT_PROFILES,
    TABLETOP_TASK_PROFILES,
    TabletopReadiness,
    build_tabletop_config,
    list_tabletop_combinations,
)


def test_tabletop_matrix_is_complete_and_has_stable_names() -> None:
    combinations = list_tabletop_combinations()
    expected_size = len(TABLETOP_TASK_PROFILES) * len(TABLETOP_EMBODIMENT_PROFILES)

    assert expected_size == 45
    assert len(combinations) == expected_size
    assert len({combination.config_name for combination in combinations}) == expected_size
    assert set(TABLETOP_CONFIG_CLASSES) == {
        combination.config_name for combination in combinations
    }


def test_reference_franka_config_contains_matrix_metadata() -> None:
    config = build_tabletop_config(
        "pick_and_place",
        "franka_droid",
        samples_per_house=2,
        max_tasks=20,
        house_inds=[0, 1],
    )

    assert config.tabletop_task == "pick_and_place"
    assert config.tabletop_embodiment == "franka_droid"
    assert config.tabletop_readiness == TabletopReadiness.REFERENCE.value
    assert config.robot_config.active_gripper_move_group_id == "gripper"
    assert config.robot_config.active_ik_move_group_ids == ["arm"]
    assert config.task_sampler_config.samples_per_house == 2
    assert config.task_sampler_config.max_tasks == 20
    assert config.task_sampler_config.house_inds == [0, 1]


def test_dual_arm_profiles_accept_an_explicit_right_gripper() -> None:
    config = build_tabletop_config(
        "packing",
        "bimanual_yam",
        active_gripper="right",
    )

    assert config.robot_config.active_gripper_move_group_id == "right_gripper"
    assert config.robot_config.active_ik_move_group_ids == ["right_arm"]
    assert config.policy_config.filter_feasible_grasps is False


def test_rby1_sequential_ik_fallback_disables_parallel_grasp_filtering() -> None:
    config = build_tabletop_config("pick", "rby1", active_gripper="left")

    assert config.robot_config.active_gripper_move_group_id == "left_gripper"
    assert config.robot_config.active_ik_move_group_ids == ["base", "torso", "left_arm"]
    assert config.policy_config.filter_feasible_grasps is False
