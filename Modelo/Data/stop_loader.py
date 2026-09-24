import csv
from Agents.bus_stop_agent import BusStopAgent

class StopLoader:

    def __init__(self, file_path):

        self.file_path = file_path
        self.stops = []

    # ==========================================
    # CARREGA OS PONTOS
    # ==========================================

    def load(self):

        self.stops = []

        with open(
            self.file_path,
            "r",
            encoding="utf-8"
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:

                stop = {
                    "stop_id": row["stop_id"],
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                    "lines": row["lines"].split("|"),
                    "road_type": row["road_type"].strip()
                }

                self.stops.append(stop)

        return self.stops

    # ==========================================
    # BUSCA UM PONTO
    # ==========================================

    def get_stop(self, stop_id):

        for stop in self.stops:

            if stop["stop_id"] == stop_id:
                return stop

        return None

    # ==========================================
    # QUANTIDADE DE PONTOS
    # ==========================================

    def size(self):

        return len(self.stops)

    # ==========================================
    # CRIA AGENTES A PARTIR DOS PONTOS
    # ==========================================

    def create_agents(self):

        agents = []

        for stop in self.stops:

            agent = BusStopAgent(
                stop_id=stop["stop_id"],
                latitude=stop["latitude"],
                longitude=stop["longitude"],
                lines=stop["lines"],
                road_type=stop["road_type"]
            )

            agents.append(agent)

        return agents