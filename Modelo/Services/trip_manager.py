from datetime import datetime, timedelta

from Simulation.bus_simulation import BusSimulation


class TripManager:

    STARTUP_LOOKBACK_MINUTES = 30

    def __init__(
        self,
        network,
        route_loader,
        schedule_loader,
        fuzzy
    ):
        self.network = network
        self.route_loader = route_loader
        self.schedule_loader = schedule_loader
        self.fuzzy = fuzzy

        self.trips = {}
        self.initialized = False

    # ==========================================================
    # UTILITÁRIOS
    # ==========================================================

    @staticmethod
    def parse_time(value):
        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            for format_ in ("%H:%M:%S", "%H:%M"):
                try:
                    parsed = datetime.strptime(value, format_)
                    now = datetime.now()

                    return parsed.replace(
                        year=now.year,
                        month=now.month,
                        day=now.day
                    )

                except ValueError:
                    continue

        raise ValueError(f"Horário inválido: {value}")

    @staticmethod
    def create_trip_id(route_id, departure_time, direction):
        return f"{route_id}_{departure_time}_{direction}"

    # ==========================================================
    # CRIAÇÃO DAS VIAGENS
    # ==========================================================

    def create_trip(self, schedule):

        route_id = schedule["route_id"]
        departure_time = schedule["start_time"]
        direction = schedule["direction"]

        trip_id = self.create_trip_id(
            route_id,
            departure_time,
            direction
        )

        if trip_id in self.trips:
            return self.trips[trip_id]

        route = self.route_loader.get_route(route_id)

        if not route:
            return None

        stop_ids = [
            stop["stop_id"]
            for stop in route
        ]

        if not stop_ids:
            return None

        simulation = BusSimulation(
            network=self.network,
            route_loader=self.route_loader,
            schedule_loader=self.schedule_loader,
            fuzzy=self.fuzzy
        )

        trip = {
            "trip_id": trip_id,
            "route_id": route_id,
            "direction": direction,
            "departure_time": departure_time,

            "simulation": simulation,

            "finished": False,
            "started": False,
            "status": "scheduled",

            "next_prediction": None,

            "last_update": None,

            "reconstruction_error": None
        }

        self.trips[trip_id] = trip

        return trip

    # ==========================================================
    # INICIALIZAÇÃO
    # ==========================================================

    def initialize(self, current_time=None):

        if current_time is None:
            current_time = datetime.now()

        startup_start = (
            current_time
            - timedelta(minutes=self.STARTUP_LOOKBACK_MINUTES)
        )

        # Cria todas as viagens da tabela de horários.
        for schedule in self.schedule_loader.schedules:
            self.create_trip(schedule)

        # Classifica cada viagem.
        for trip in self.trips.values():

            departure_time = self.parse_time(
                trip["departure_time"]
            )

            # Viagem futura.
            if departure_time > current_time:

                trip["status"] = "scheduled"
                trip["started"] = False
                trip["finished"] = False

                continue

            # Viagem antiga demais para reconstrução.
            if departure_time < startup_start:

                trip["status"] = "not_tracked"
                trip["started"] = False
                trip["finished"] = False

                continue

            # Viagem dentro da janela de 30 minutos.
            try:

                self.reconstruct_trip(
                    trip,
                    current_time
                )

            except Exception as error:

                trip["status"] = "not_tracked"
                trip["reconstruction_error"] = str(error)

        self.initialized = True

        return self.get_all_states()

    def load_scheduled_trips(self, current_time=None):
        return self.initialize(current_time)

    # ==========================================================
    # CONSULTA DAS VIAGENS
    # ==========================================================

    def get_trip(self, trip_id):
        return self.trips.get(trip_id)

    def get_trips(self):
        return list(self.trips.values())

    def get_active_trips(self):
        return [
            trip
            for trip in self.trips.values()
            if trip["status"] == "active"
        ]

    def get_scheduled_trips(self):
        return [
            trip
            for trip in self.trips.values()
            if trip["status"] == "scheduled"
        ]

    def get_not_tracked_trips(self):
        return [
            trip
            for trip in self.trips.values()
            if trip["status"] == "not_tracked"
        ]

    def get_finished_trips(self):
        return [
            trip
            for trip in self.trips.values()
            if trip["status"] == "finished"
        ]

    # ==========================================================
    # ESTADO
    # ==========================================================

    def get_trip_state(self, trip):

        simulation = trip["simulation"]

        state = simulation.get_state()

        return {
            "trip_id": trip["trip_id"],
            "route_id": trip["route_id"],
            "direction": trip["direction"],
            "departure_time": trip["departure_time"],

            "current_stop": state["current_stop"],
            "current_time": state["current_time"],

            "previous_delay": state["previous_delay"],
            "previous_confidence": state["previous_confidence"],

            "status": trip["status"],
            "finished": trip["finished"],

            "next_prediction": trip["next_prediction"]
        }

    def get_all_states(self):

        return [
            self.get_trip_state(trip)
            for trip in self.trips.values()
        ]

    # ==========================================================
    # RECONSTRUÇÃO
    # ==========================================================

    def calculate_reconstruction_segment(
        self,
        simulation,
        next_agent,
        route_id
    ):

        context = simulation.get_context(next_agent)

        return next_agent.calculate_previous_segment_from_context(
            route_id,
            context
        )

    def reconstruct_trip(
        self,
        trip,
        current_time=None
    ):

        if current_time is None:
            current_time = datetime.now()

        departure_time = self.parse_time(
            trip["departure_time"]
        )

        # Ainda não saiu.
        if current_time < departure_time:

            trip["status"] = "scheduled"
            trip["started"] = False
            trip["finished"] = False

            return

        # Fora da janela de reconstrução.
        startup_start = (
            current_time
            - timedelta(minutes=self.STARTUP_LOOKBACK_MINUTES)
        )

        if departure_time < startup_start:

            trip["status"] = "not_tracked"
            trip["started"] = False
            trip["finished"] = False

            return

        route = self.route_loader.get_route(
            trip["route_id"]
        )

        if not route:

            trip["status"] = "not_tracked"
            return

        stop_ids = [
            stop["stop_id"]
            for stop in route
        ]

        if not stop_ids:

            trip["status"] = "not_tracked"
            return

        simulation = trip["simulation"]

        # Estado inicial da viagem.
        simulation.current_route = trip["route_id"]
        simulation.current_stop = stop_ids[0]
        simulation.current_time = departure_time

        simulation.previous_delay = 0.0
        simulation.previous_confidence = 100.0

        trip["next_prediction"] = None
        trip["finished"] = False
        trip["started"] = True
        trip["reconstruction_error"] = None

        elapsed_seconds = (
            current_time - departure_time
        ).total_seconds()

        accumulated_time = 0.0

        # Percorre a rota somente para descobrir
        # em qual trecho o ônibus deveria estar.
        for index in range(len(stop_ids) - 1):

            current_stop_id = stop_ids[index]
            next_stop_id = stop_ids[index + 1]

            current_agent = self.network.get_agent(
                current_stop_id
            )

            next_agent = self.network.get_agent(
                next_stop_id
            )

            if current_agent is None or next_agent is None:

                trip["status"] = "not_tracked"
                return

            try:

                segment = self.calculate_reconstruction_segment(
                    simulation,
                    next_agent,
                    trip["route_id"]
                )

            except Exception as error:

                trip["status"] = "not_tracked"
                trip["reconstruction_error"] = str(error)

                return

            segment_time = float(
                segment["travel_time_seconds"]
            )

            # O ônibus ainda está neste trecho.
            if accumulated_time + segment_time > elapsed_seconds:

                segment_elapsed = (
                    elapsed_seconds
                    - accumulated_time
                )

                segment_remaining = (
                    segment_time
                    - segment_elapsed
                )

                arrival_datetime = (
                    departure_time
                    + timedelta(
                        seconds=(
                            accumulated_time
                            + segment_time
                        )
                    )
                )

                simulation.current_stop = current_stop_id

                simulation.current_time = (
                    departure_time
                    + timedelta(
                        seconds=accumulated_time
                    )
                )

                trip["status"] = "active"
                trip["finished"] = False

                trip["next_prediction"] = {

                    "current_stop": current_stop_id,

                    "next_stop": next_stop_id,

                    "departure_time": (
                        simulation.current_time
                    ),

                    "arrival_time": (
                        arrival_datetime.strftime(
                            "%H:%M:%S"
                        )
                    ),

                    "elapsed_seconds": elapsed_seconds,

                    "segment_elapsed_seconds": (
                        segment_elapsed
                    ),

                    "segment_remaining_seconds": (
                        segment_remaining
                    ),

                    "segment": segment
                }

                trip["last_update"] = current_time

                return

            # O trecho já terminou.
            accumulated_time += segment_time

        # Chegou ao último ponto.
        simulation.current_stop = stop_ids[-1]

        simulation.current_time = (
            departure_time
            + timedelta(
                seconds=accumulated_time
            )
        )

        trip["status"] = "finished"
        trip["finished"] = True
        trip["started"] = True
        trip["next_prediction"] = None
        trip["last_update"] = current_time

    # ==========================================================
    # INÍCIO DE UMA VIAGEM
    # ==========================================================

    def start_trip(
        self,
        trip,
        current_time=None
    ):

        if current_time is None:
            current_time = datetime.now()

        departure_time = self.parse_time(
            trip["departure_time"]
        )

        route = self.route_loader.get_route(
            trip["route_id"]
        )

        if not route:

            trip["status"] = "not_tracked"
            return

        stop_ids = [
            stop["stop_id"]
            for stop in route
        ]

        if not stop_ids:

            trip["status"] = "not_tracked"
            return

        simulation = trip["simulation"]

        simulation.start_trip(
            route_id=trip["route_id"],
            origin_stop=stop_ids[0],
            departure_time=departure_time
        )

        trip["started"] = True
        trip["finished"] = False
        trip["status"] = "active"

        trip["next_prediction"] = None

        trip["last_update"] = current_time

        # ======================================================
        # IMPORTANTE:
        # Calcula SOMENTE o próximo trecho.
        # Não calcula a rota inteira.
        # ======================================================

        try:

            result = simulation.calculate_next_prediction(
                destination_stop=stop_ids[-1]
                ,
            current_time=current_time
            )

        except Exception as error:

            trip["status"] = "not_tracked"
            trip["reconstruction_error"] = str(error)

            return

        if not result:

            trip["status"] = "finished"
            trip["finished"] = True

            return

        # BusSimulation.calculate_next_prediction()
        # retorna:
        #
        # {
        #     "next_prediction": {...},
        #     "destination_prediction": {...},
        #     "future_predictions": [...]
        # }
        #
        # Para o TripManager, só interessa o próximo trecho.

        if "next_prediction" in result:

            trip["next_prediction"] = (
                result["next_prediction"]
            )

        else:

            trip["next_prediction"] = result

    # ==========================================================
    # ATUALIZAÇÃO DE VIAGEM ATIVA
    # ==========================================================

    def update_active_trip(
        self,
        trip,
        current_time=None
    ):

        if current_time is None:
            current_time = datetime.now()

        simulation = trip["simulation"]

        route = self.route_loader.get_route(
            trip["route_id"]
        )

        if not route:

            trip["status"] = "not_tracked"
            return

        stop_ids = [
            stop["stop_id"]
            for stop in route
        ]

        # Já chegou ao destino.
        if simulation.current_stop == stop_ids[-1]:

            trip["status"] = "finished"
            trip["finished"] = True
            trip["next_prediction"] = None

            return

        # ======================================================
        # Se não existe previsão, calcula SOMENTE o próximo
        # trecho.
        # ======================================================

        if trip["next_prediction"] is None:

            try:

                result = simulation.calculate_next_prediction(
    destination_stop=stop_ids[-1],
    current_time=current_time
)

            except Exception as error:

                trip["status"] = "not_tracked"
                trip["reconstruction_error"] = str(error)

                return

            if not result:

                trip["status"] = "finished"
                trip["finished"] = True

                return

            if "next_prediction" in result:

                trip["next_prediction"] = (
                    result["next_prediction"]
                )

            else:

                trip["next_prediction"] = result

        # ======================================================
        # Verifica se chegou a hora de concretizar o próximo
        # trecho.
        # ======================================================

        prediction = trip["next_prediction"]

        arrival_time = self.parse_time(
            prediction["arrival_time"]
        )

        if current_time < arrival_time:

            trip["last_update"] = current_time

            return

        # ======================================================
        # O horário previsto chegou.
        # Agora avançamos o estado REAL da simulação.
        # ======================================================

        try:

            step = simulation.advance(
                realtime=False
            )

        except Exception as error:

            trip["status"] = "not_tracked"
            trip["reconstruction_error"] = str(error)

            return

        # ======================================================
        # Verifica se terminou.
        # ======================================================

        if step.get("finished"):

            trip["status"] = "finished"
            trip["finished"] = True
            trip["next_prediction"] = None
            trip["last_update"] = current_time

            return

        trip["next_prediction"] = None
        trip["last_update"] = current_time

        # Chegou ao último ponto.
        if simulation.current_stop == stop_ids[-1]:

            trip["status"] = "finished"
            trip["finished"] = True
            trip["next_prediction"] = None

            return

        # ======================================================
        # Depois de chegar ao ponto atual, calcula SOMENTE
        # o próximo trecho.
        # ======================================================

        try:

            result = simulation.calculate_next_prediction(
    destination_stop=stop_ids[-1],
    current_time=current_time
)

        except Exception as error:

            trip["status"] = "not_tracked"
            trip["reconstruction_error"] = str(error)

            return

        if not result:

            trip["status"] = "finished"
            trip["finished"] = True
            trip["next_prediction"] = None

            return

        if "next_prediction" in result:

            trip["next_prediction"] = (
                result["next_prediction"]
            )

        else:

            trip["next_prediction"] = result

    # ==========================================================
    # ATUALIZAÇÃO DE UMA VIAGEM ESPECÍFICA
    # ==========================================================

    def update_trip(
        self,
        trip_id,
        current_time=None
    ):

        if current_time is None:
            current_time = datetime.now()

        trip = self.get_trip(trip_id)

        if trip is None:
            return None

        self.update(current_time)

        return trip

    # ==========================================================
    # ATUALIZAÇÃO GERAL
    # ==========================================================

    def update(self, current_time=None):

        if current_time is None:
            current_time = datetime.now()

        # Inicialização acontece somente uma vez.
        if not self.initialized:

            self.initialize(current_time)

        # Monitora todas as viagens.
        for trip in self.trips.values():

            # ==================================================
            # VIAGEM AGENDADA
            # ==================================================

            if trip["status"] == "scheduled":

                departure_time = self.parse_time(
                    trip["departure_time"]
                )

                # Ainda não chegou o horário.
                if current_time < departure_time:
                    continue

                # Chegou o horário.
                self.start_trip(
                    trip,
                    current_time
                )

            # ==================================================
            # VIAGEM ATIVA
            # ==================================================

            if trip["status"] == "active":

                self.update_active_trip(
                    trip,
                    current_time
                )

            # ==================================================
            # VIAGEM FINALIZADA
            # ==================================================

            elif trip["status"] == "finished":

                continue

            # ==================================================
            # VIAGEM QUE NÃO PÔDE SER ACOMPANHADA
            # ==================================================

            elif trip["status"] == "not_tracked":

                continue

        return self.get_all_states()