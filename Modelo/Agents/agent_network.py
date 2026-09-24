from .travel_time import TravelTimeCalculator


class AgentNetwork:

    def __init__(self):

        self.agents = {}
        self.travel_time_calculator = TravelTimeCalculator()
        self.segment_distances = {}

    # ==========================================
    # ADICIONA UM AGENTE
    # ==========================================

    def add_agent(self, agent):

        self.agents[agent.stop_id] = agent

        agent.set_network(self)


    # ==========================================
    # ADICIONA VÁRIOS AGENTES
    # ==========================================

    def add_agents(self, agents):

        for agent in agents:
            self.add_agent(agent)


    # ==========================================
    # BUSCA UM AGENTE
    # ==========================================

    def get_agent(self, stop_id):

        return self.agents.get(stop_id)


    # ==========================================
    # CONECTA DOIS AGENTES
    # ==========================================

    def connect_agents(
    self,
    previous_id,
    next_id,
    route_id
):

        previous_agent = self.get_agent(
            previous_id
        )

        next_agent = self.get_agent(
            next_id
        )

        if previous_agent is None:
            raise ValueError(
                f"Agente não encontrado: {previous_id}"
            )

        if next_agent is None:
            raise ValueError(
                f"Agente não encontrado: {next_id}"
            )

        previous_agent.set_next_agent(
            next_agent,
            route_id
        )

        next_agent.set_previous_agent(
            previous_agent,
            route_id
        )

    # ==========================================
    # CONECTA UMA ROTA COMPLETA
    # ==========================================

    def connect_route(self, stop_ids,route_id):

       for i in range(len(stop_ids) - 1):

        current_id = stop_ids[i]
        next_id = stop_ids[i + 1]

        self.connect_agents(
            current_id,
            next_id,
            route_id
        )


    # ==========================================
    # QUANTIDADE DE AGENTES
    # ==========================================

    def size(self):

        return len(self.agents)


    # ==========================================
    # REPRESENTAÇÃO DA REDE
    # ==========================================

    def __repr__(self):

        return (
            f"AgentNetwork("
            f"agents={self.size()}"
            f")"
        )

 # ==========================================
    # ARMAZENA DISTÂNCIA REAL DE UM TRECHO
    # ==========================================

    def set_segment_distance(
        self,
        previous_id,
        next_id,
        distance_meters,
        route_id=None
    ):

        key = (
            route_id,
            previous_id,
            next_id
        )

        self.segment_distances[key] = float(
            distance_meters
        )


    # ==========================================
    # BUSCA DISTÂNCIA REAL DO TRECHO
    # ==========================================

    def get_segment_distance(
        self,
        previous_id,
        next_id,
        route_id=None
    ):

        key = (
            route_id,
            previous_id,
            next_id
        )

        return self.segment_distances.get(key)
    # ==========================================
    # CALCULA TEMPO ENTRE DOIS AGENTES
    # ==========================================

    def calculate_segment_time(
    self,
    previous_id,
    next_id,
    speed_kmh,
    route_id=None
):

        previous_agent = self.get_agent(
            previous_id
        )

        next_agent = self.get_agent(
            next_id
        )

        if previous_agent is None:
            raise ValueError(
                f"Agente não encontrado: {previous_id}"
            )

        if next_agent is None:
            raise ValueError(
                f"Agente não encontrado: {next_id}"
            )

        # ==========================================
        # BUSCA DISTÂNCIA REAL DO TRECHO
        # ==========================================

        distance = self.get_segment_distance(
            previous_id,
            next_id,
            route_id
        )

        # ==========================================
        # FALLBACK PARA HAVERSINE
        # ==========================================

        if distance is None:

            distance = TravelTimeCalculator.haversine_distance(
                previous_agent.latitude,
                previous_agent.longitude,
                next_agent.latitude,
                next_agent.longitude
            )

        # ==========================================
        # CALCULA TEMPO
        # ==========================================

        travel_time = TravelTimeCalculator.calculate(
            distance,
            speed_kmh
        )

        return {
            "previous_agent": previous_id,
            "next_agent": next_id,
            "distance_meters": distance,
            "speed_kmh": speed_kmh,
            "travel_time_seconds": travel_time
        }

    # ==========================================
    # CALCULA TEMPO TOTAL DA ROTA
    # ==========================================

    def calculate_route_time(
        self,
        stop_ids,
        speed_kmh,
        route_id=None
    ):

        segments = []
        total_time = 0.0
        total_distance = 0.0

        for i in range(len(stop_ids) - 1):

            segment = self.calculate_segment_time(
                stop_ids[i],
                stop_ids[i + 1],
                speed_kmh,
                route_id
            )

            segments.append(segment)

            total_time += segment[
                "travel_time_seconds"
            ]

            total_distance += segment[
                "distance_meters"
            ]

        return {
            "segments": segments,
            "total_distance_meters": total_distance,
            "total_time_seconds": total_time
        }

    # ==========================================
    # CONECTA ROTAS A PARTIR DO ROUTE LOADER
    # ==========================================

    def connect_routes_from_loader(self, route_loader):

        for route_id in route_loader.get_route_ids():

            route = route_loader.get_route(route_id)

            stop_ids = [
                stop["stop_id"]
                for stop in route
            ]

            self.connect_route(
                stop_ids,
                route_id
            )