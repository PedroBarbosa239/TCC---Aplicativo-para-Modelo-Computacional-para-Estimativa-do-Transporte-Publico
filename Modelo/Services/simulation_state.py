from enum import Enum


class SimulationState(Enum):

    IDLE = "idle"
    RUNNING = "running"
    WAITING_ARRIVAL = "waiting_arrival"
    FINISHED = "finished"
    ERROR = "error"
    STOPPED = "stopped"