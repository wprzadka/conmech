# Standardize data! (from -1 to 1)
DIM = 2

DENS = 0.01
MU = 0.01
LA = 0.01
TH = 0.01
ZE = 0.01

OBSTACLE_HARDNESS = 0.04
OBSTACLE_FRICTION = 0.004

NORMALIZE_ROTATE = False
############

# "meshzoo" "pygmsh_rectangle" "pygmsh_circle" "pygmsh_spline" "pygmsh_polygon" "dmsh" "cross"

TRAIN_SCALE = 1.0
PRINT_SCALE = 1.0  # 2.0
SIMULATOR_SCALE = 1.0

MESH_DENSITY = 16
ADAPTIVE_MESH = True
CALCULATOR_MODE = "optimization"  # "function" # "optimization"
SIMULATE_DIRTY_DATA = True

TIMESTEP = 0.01

############

FORCES_RANDOM_SCALE = 1.3
U_RANDOM_SCALE = 0.2
V_RANDOM_SCALE = 2.5
OBSTACLE_ORIGIN_SCALE = 2.0 * TRAIN_SCALE

DATA_ZERO_FORCES = 0.5
DATA_ROTATE_VELOCITY = 0.5

U_NOISE_GAMMA = 0.1
U_IN_RANDOM_FACTOR = 0.005 * U_RANDOM_SCALE
V_IN_RANDOM_FACTOR = 0.005 * V_RANDOM_SCALE

############

FINAL_TIME = 4.0  #!#
EPISODE_STEPS = int(FINAL_TIME / TIMESTEP)

############

DATA_FOLDER = f"{MESH_DENSITY}"  #!#
PRINT_DATA_CUTOFF = 1

############

VALIDATE_AT_EPOCHS = 20
DRAW_AT_MINUTES = 60  #!#
PRINT_SKIP = 0.1
DRAW_DETAILED = True


BATCH_SIZE = 128  #!#
VALID_BATCH_SIZE = 32  #!#
SYNTHETIC_BATCHES_IN_EPOCH = 512  #!#
SYNTHETIC_SOLVERS_COUNT = BATCH_SIZE * SYNTHETIC_BATCHES_IN_EPOCH

############

DATALOADER_WORKERS = 4
GENERATION_WORKERS = 2
GENERATION_MEMORY_LIMIT_GB = 24.0 / GENERATION_WORKERS
TOTAL_MEMORY_LIMIT_GB = 29.0

############

DROPOUT_RATE = 0.1  # 0.05
SKIP = True
# GRADIENT_CLIP = 10.0

ATTENTION_HEADS = None  # 1  # None 1 3 5

INITIAL_LR = 1e-4
LR_GAMMA = 1.0  # 0.999
FINAL_LR = 1e-6

LATENT_DIM = 128
ENC_LAYER_COUNT = 2
PROC_LAYER_COUNT = 0
DEC_LAYER_COUNT = 2
MESSAGE_PASSES = 8  # 5 # 10


VERTEX_DATA_DIM = 10
EDGE_DATA_DIM = 12
ALL_VERTEX_DIM = LATENT_DIM + VERTEX_DATA_DIM + DIM
