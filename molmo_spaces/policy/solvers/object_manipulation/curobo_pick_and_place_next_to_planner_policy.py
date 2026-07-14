"""CuRobo execution for pick-and-place-next-to tasks."""

import numpy as np

from molmo_spaces.policy.solvers.object_manipulation.curobo_pick_and_place_planner_policy import (
    CuroboPickAndPlacePlannerPolicy,
)
from molmo_spaces.policy.solvers.object_manipulation.pick_and_place_next_to_planner_policy import (
    PickAndPlaceNextToPlannerPolicy,
)


class CuroboPickAndPlaceNextToPlannerPolicy(CuroboPickAndPlacePlannerPolicy):
    """Use the next-to task's placement sampler with CuRobo trajectory execution."""

    def _get_place_poses(self) -> np.ndarray:
        task_config = self.config.task_config
        object_manager = self.task.env.object_managers[self.task.env.current_batch_index]
        pickup_obj = object_manager.get_object_by_name(task_config.pickup_obj_name)
        place_receptacle = object_manager.get_object_by_name(task_config.place_receptacle_name)

        pregrasp_poses = self.pre_grasp_poses
        is_batch = pregrasp_poses.ndim == 3
        pose_batch = pregrasp_poses if is_batch else pregrasp_poses[np.newaxis, ...]

        # The generic next-to policy samples one collision-free target on the shared support
        # surface. Apply its translation to every candidate grasp so CuRobo can still choose
        # among orientations during batch planning.
        _, reference_place_pose, _ = PickAndPlaceNextToPlannerPolicy._get_placement_poses(
            self,
            pose_batch[0],
            pickup_obj,
            place_receptacle,
        )
        translation = reference_place_pose[:3, 3] - pose_batch[0, :3, 3]
        place_poses = pose_batch.copy()
        place_poses[:, :3, 3] += translation

        return place_poses if is_batch else place_poses[0]
