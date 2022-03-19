import numpy as np
from conmech.dataclass.body_coeff import BodyCoeff
from conmech.dataclass.mesh_data import MeshData
from conmech.dataclass.obstacle_coeff import ObstacleCoeff
from conmech.dataclass.time_data import TimeData
from conmech.helpers import nph
from deep_conmech.common import config
from deep_conmech.simulator.setting.setting_forces import *
from numba import njit


def get_penetration_norm_internal(
    nodes, obstacle_nodes, obstacle_nodes_normals, dot=np.dot
):
    projection = (-1) * dot((nodes - obstacle_nodes), obstacle_nodes_normals)
    return (projection > 0) * projection


def get_penetration_norm(nodes, obstacle_nodes, obstacle_nodes_normals):
    return get_penetration_norm_internal(
        nodes, obstacle_nodes, obstacle_nodes_normals, dot=nph.elementwise_dot
    ).reshape(-1, 1)

get_penetration_norm_numba = numba.njit(get_penetration_norm_internal)


####


def obstacle_resistance_potential_normal(penetration_norm, hardness, time_step):
    return hardness * 0.5 * (penetration_norm ** 2) * ((1.0 / time_step) ** 2)

obstacle_resistance_potential_normal_numba = numba.njit(
    obstacle_resistance_potential_normal
)

def obstacle_resistance_potential_tangential_internal(
    penetration_norm,
    tangential_velocity,
    friction,
    time_step,
    norm=nph.euclidean_norm_numba,
):
    return (
        (penetration_norm > 0)
        * friction
        * norm(tangential_velocity)
        * (1.0 / time_step)
    )


def obstacle_resistance_potential_tangential(
    penetration, tangential_velocity, friction, time_step
):
    return obstacle_resistance_potential_tangential_internal(
        penetration, tangential_velocity, friction, time_step, norm=lambda x : nph.euclidean_norm(x, keepdims=True)
    )

obstacle_resistance_potential_tangential_numba = numba.njit(
    obstacle_resistance_potential_tangential_internal
)


def integrate(
    nodes,
    nodes_normals,
    obstacle_nodes,
    obstacle_nodes_normals,
    v,
    nodes_volume,
    hardness,
    friction,
    time_step,
):
    penetration_norm = get_penetration_norm(
        nodes, obstacle_nodes, obstacle_nodes_normals
    )

    v_tangential = nph.get_tangential(v, nodes_normals)

    resistance_normal = obstacle_resistance_potential_normal(
        penetration_norm, hardness, time_step
    )
    resistance_tangential = obstacle_resistance_potential_tangential(
        penetration_norm, v_tangential, friction, time_step
    )
    result = (nodes_volume * (resistance_normal + resistance_tangential)).sum()
    return result


#@njit
def integrate_numba(
    nodes,
    nodes_normals,
    obstacle_nodes,
    obstacle_nodes_normals,
    v,
    nodes_volume,
    hardness,
    friction,
    time_step,
):
    result = 0.0
    for i in range(len(nodes)):
        penetration = get_penetration_norm_numba(
            nodes[i], obstacle_nodes[i], obstacle_nodes_normals[i]
        )

        v_tangential = nph.get_tangential_numba(v[i], nodes_normals[i])

        resistance_normal = obstacle_resistance_potential_normal_numba(
            penetration, hardness, time_step
        )
        resistance_tangential = obstacle_resistance_potential_tangential_numba(
            penetration, v_tangential, friction, time_step
        )

        result += nodes_volume[i].item() * (resistance_normal + resistance_tangential)
    return result


def L2_obstacle(
    a,
    C,
    E,
    boundary_v_old,
    boundary_nodes,
    boundary_normals,
    boundary_obstacle_nodes,
    boundary_obstacle_normals,
    boundary_nodes_volume: np.ndarray,
    obstacle_coeff: ObstacleCoeff,
    time_step: float,
):
    value = L2_new(a, C, E)

    boundary_nodes_count = boundary_v_old.shape[0]
    boundary_a = a[:boundary_nodes_count, :]  # TODO: boundary slice

    boundary_v_new = boundary_v_old + time_step * boundary_a
    boundary_nodes_new = boundary_nodes + time_step * boundary_v_new

    args = (
        boundary_nodes_new,
        boundary_normals,
        boundary_obstacle_nodes,
        boundary_obstacle_normals,
        boundary_v_new,
        boundary_nodes_volume,
        obstacle_coeff.hardness,
        obstacle_coeff.friction,
        time_step,
    )

    is_numpy = isinstance(a, np.ndarray)
    boundary_integral = integrate_numba(*args) if is_numpy else integrate(*args)
    return value + boundary_integral


@njit
def get_closest_obstacle_to_boundary_numba(boundary_nodes, obstacle_nodes):
    boundary_obstacle_indices = np.zeros((len(boundary_nodes)), dtype=numba.int64)

    for i in range(len(boundary_nodes)):
        distances = nph.euclidean_norm_numba(obstacle_nodes - boundary_nodes[i])
        boundary_obstacle_indices[i] = distances.argmin()

    return boundary_obstacle_indices


class SettingObstacles(SettingForces):
    def __init__(
        self,
        mesh_data: MeshData,
        body_coeff: BodyCoeff,
        obstacle_coeff: ObstacleCoeff,
        time_data: TimeData,
        create_in_subprocess,
    ):
        super().__init__(
            mesh_data=mesh_data,
            body_coeff=body_coeff,
            time_data=time_data,
            create_in_subprocess=create_in_subprocess,
        )
        self.obstacle_coeff = obstacle_coeff
        self.obstacles = None
        self.clear()

    def prepare(self, forces):
        super().prepare(forces)
        self.boundary_obstacle_indices = get_closest_obstacle_to_boundary_numba(
            self.boundary_nodes, self.obstacle_origins
        )

    def clear(self):
        super().clear()
        self.boundary_obstacle_nodes_indices = None

    def set_obstacles(self, obstacles_unnormalized):
        self.obstacles = obstacles_unnormalized
        self.obstacles[0, ...] = nph.normalize_euclidean_numba(self.obstacles[0, ...])

    def get_normalized_L2_obstacle_np(self):
        return lambda normalized_boundary_a_vector: L2_obstacle(
            nph.unstack(normalized_boundary_a_vector, self.dim),
            self.C_boundary,
            self.normalized_E_boundary,
            self.normalized_boundary_v_old,
            self.normalized_boundary_nodes,
            self.normalized_boundary_normals,
            self.normalized_boundary_obstacle_nodes,
            self.normalized_boundary_obstacle_normals,
            self.boundary_nodes_volume,
            self.obstacle_coeff,
            self.time_step,
        )

    @property
    def obstacle_normals(self):
        return self.obstacles[0, ...]

    @property
    def obstacle_origins(self):
        return self.obstacles[1, ...]

    @property
    def obstacle_nodes(self):
        return self.obstacles[1, ...]

    @property
    def obstacle_nodes_normals(self):
        return self.obstacles[0, ...]

    @property
    def boundary_obstacle_nodes(self):
        return self.obstacle_nodes[self.boundary_obstacle_indices]

    @property
    def boundary_obstacle_normals(self):
        return self.obstacle_normals[self.boundary_obstacle_indices]

    @property
    def normalized_boundary_obstacle_nodes(self):
        return self.normalize_rotate(
            self.boundary_obstacle_nodes - self.mean_moved_nodes
        )

    @property
    def normalized_boundary_obstacle_normals(self):
        return self.normalize_rotate(self.boundary_obstacle_normals)

    @property
    def normalized_obstacle_normals(self):
        return self.normalize_rotate(self.obstacle_normals)

    @property
    def normalized_obstacle_origins(self):
        return self.normalize_rotate(self.obstacle_origins - self.mean_moved_nodes)

    @property
    def obstacle_normal(self):
        return self.obstacle_normals[0]

    @property
    def obstacle_origin(self):
        return self.obstacle_origins[0]

    @property
    def normalized_obstacle_normal(self):
        return self.normalized_obstacle_normals[0]

    @property
    def normalized_obstacle_origin(self):
        return self.normalized_obstacle_origins[0]

    @property
    def boundary_v_old(self):
        return self.v_old[self.boundary_nodes_indices]

    @property
    def boundary_a_old(self):
        return self.a_old[self.boundary_nodes_indices]

    @property
    def normalized_boundary_v_old(self):
        return self.normalized_v_old[self.boundary_nodes_indices]

    @property
    def normalized_boundary_nodes(self):
        return self.normalized_points[self.boundary_nodes_indices]

    @property
    def boundary_penetration_norm(self):
        return get_penetration_norm(
            self.boundary_nodes,
            self.boundary_obstacle_nodes,
            self.boundary_obstacle_normals,
        )

    @property
    def boundary_penetration(self):
        boundary_penetration_norm = self.boundary_penetration_norm
        return boundary_penetration_norm * self.boundary_obstacle_normals

    @property
    def normalized_boundary_penetration(self):
        return self.normalize_rotate(self.boundary_penetration)

    #######

    @property
    def normalized_boundary_v_tangential(self):
        return nph.get_tangential(
            self.normalized_boundary_v_old, self.normalized_boundary_normals
        ) * (self.boundary_penetration_norm > 0)

    @property
    def boundary_v_tangential(self):
        return nph.get_tangential(self.boundary_v_old, self.boundary_normals)

    @property
    def resistance_normal(self):
        return obstacle_resistance_potential_normal(
            self.boundary_penetration_norm, self.obstacle_coeff.hardness, self.time_step
        )

    @property
    def resistance_tangential(self):
        return obstacle_resistance_potential_tangential(
            self.boundary_penetration_norm,
            self.boundary_v_tangential,
            self.obstacle_coeff.friction,
            self.time_step,
        )
