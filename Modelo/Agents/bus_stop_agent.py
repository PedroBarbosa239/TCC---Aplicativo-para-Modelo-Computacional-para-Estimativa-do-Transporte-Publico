from .agent_message import AgentMessage
from .travel_time import TravelTimeCalculator

from datetime import datetime, timedelta


class BusStopAgent:

    def __init__(
        self,
        stop_id,
        latitude,
        longitude,
        lines=None,
        road_type="unknown"
       
    ):

        self.stop_id = stop_id

        # ==========================================
        # MENSAGENS RECEBIDAS
        # ==========================================

        self.received_messages = []

        # ==========================================
        # DADOS ESPACIAIS
        # ==========================================

        self.latitude = latitude
        self.longitude = longitude

    

        # ==========================================
        # LINHAS QUE PASSAM PELO PONTO
        # ==========================================

        self.lines = (
            lines
            if lines is not None
            else []
        )
        self.road_type = road_type
        # ==========================================
        # VIZINHANÇA DOS AGENTES
        # ==========================================

        self.previous_agents = {}
        self.next_agents = {}

        # ==========================================
        # REDE
        # ==========================================

        self.network = None

        # ==========================================
        # ESTIMATIVA E CONFIANÇA
        # ==========================================

        self.confidence = 0.0
        self.estimated_delay = 0.0

        # ==========================================
        # TEMPO DESDE O AGENTE ANTERIOR
        # ==========================================

        self.travel_time_from_previous = 0.0

    # ==========================================
    # CONFIGURA A REDE
    # ==========================================

    def set_network(self, network):

        self.network = network

    # ==========================================
    # CONECTA AGENTE ANTERIOR
    # ==========================================

    def set_previous_agent(
        self,
        agent,
        route_id=None
    ):

        if route_id is None:
            route_id = "default"

        self.previous_agents[route_id] = agent

    # ==========================================
    # CONECTA PRÓXIMO AGENTE
    # ==========================================

    def set_next_agent(
        self,
        agent,
        route_id=None
    ):

        if route_id is None:
            route_id = "default"

        self.next_agents[route_id] = agent

    # ==========================================
    # ADICIONA LINHA AO PONTO
    # ==========================================

    def add_line(self, line):

        if line not in self.lines:
            self.lines.append(line)

    # ==========================================
    # RECEBE MENSAGEM
    # ==========================================

    def receive_message(self, message):

        self.received_messages.append(message)

    # ==========================================
    # PROCESSA MENSAGEM
    # ==========================================

    def process_message(self, message):

        self.estimated_delay = message.estimated_delay
        self.confidence = message.confidence

        return {
            "stop_id": self.stop_id,
            "estimated_delay": self.estimated_delay,
            "confidence": self.confidence
        }

    # ==========================================
    # CRIA MENSAGEM
    # ==========================================
    def create_message(
        self,
        route_id,
        departure_time,
        arrival_time
    ):

        return AgentMessage(
            source_agent=self.stop_id,
            route_id=route_id,
            departure_time=departure_time,
            arrival_time=arrival_time,
            estimated_delay=self.estimated_delay,
            confidence=self.confidence
        )

    # ==========================================
    # ENVIA PARA UM PRÓXIMO AGENTE
    # ==========================================

    def send_to_next(
        self,
        route_id,
        departure_time,
        arrival_time
    ):

        next_agent = self.next_agents.get(
            route_id
        )

        if next_agent is None:
            return False

        message = self.create_message(
            route_id=route_id,
            departure_time=departure_time,
            arrival_time=arrival_time
        )

        next_agent.receive_message(
            message
        )

        return True

    # ==========================================
    # REPRESENTAÇÃO DO AGENTE
    # ==========================================

    def __repr__(self):

        return (
            f"BusStopAgent("
            f"id={self.stop_id}, "
            f"lat={self.latitude}, "
            f"lon={self.longitude}, "
            f"lines={self.lines}"
            f")"
        )

    # ==========================================
    # ESTIMA VELOCIDADE DO TRECHO
    # ==========================================

    def estimate_speed(
        self,
        current_speed,
        free_speed
    ):
        """
        Estima a velocidade utilizada no trecho.

        A velocidade atual da via é utilizada como
        referência, limitada pela velocidade livre
        fornecida pela API.

        Retorno:
            velocidade estimada em km/h
        """

        if current_speed <= 0:
            raise ValueError("A velocidade atual deve ser maior que zero.")

        if free_speed <= 0:
            raise ValueError("A velocidade livre deve ser maior que zero.")

        speed = min(current_speed, free_speed)

        factor = self.get_road_speed_factor()

        return speed * factor
    
    def calculate_previous_segment_from_context(
        self,
        route_id,
        context
    ):
        """
        Calcula o tempo do trecho anterior utilizando
        os dados brutos de velocidade presentes no contexto.

        O contexto deve possuir a estrutura:

        {
            "raw": {
                "current_speed": ...,
                "free_speed": ...
            },
            "normalized": {
                ...
            }
        }
        """

        if self.network is None:

            raise ValueError(
                f"O agente {self.stop_id} "
                "não está associado a uma rede."
            )

        # ==========================================
        # BUSCA O AGENTE ANTERIOR
        # ==========================================

        previous_agent = self.previous_agents.get(
            route_id
        )

        if previous_agent is None:

            raise ValueError(
                f"O agente {self.stop_id} "
                f"não possui agente anterior "
                f"na linha {route_id}."
            )

        # ==========================================
        # OBTÉM OS DADOS BRUTOS
        # ==========================================

        raw_context = context.get("raw", context)

        current_speed = raw_context.get(
            "current_speed"
        )

        free_speed = raw_context.get(
            "free_speed"
        )

        if current_speed is None:

            raise ValueError(
                "O contexto não possui "
                "'current_speed'."
            )

        if free_speed is None:

            raise ValueError(
                "O contexto não possui "
                "'free_speed'."
            )

        # ==========================================
        # ESTIMA A VELOCIDADE
        # ==========================================

        estimated_speed = self.estimate_speed(
            current_speed,
            free_speed
        )

        # ==========================================
        # CALCULA DISTÂNCIA
        # ==========================================

        distance = TravelTimeCalculator.haversine_distance(
            previous_agent.latitude,
            previous_agent.longitude,
            self.latitude,
            self.longitude
        )

       # ==========================================
        # CALCULA TEMPO
        # ==========================================

        travel_time = TravelTimeCalculator.calculate(
            distance,
            estimated_speed
        )

        signal_delay = self.get_signal_delay()
        boarding_time = self.get_boarding_time()

        total_travel_time = travel_time + signal_delay + boarding_time
        print(
    f"[TRECHO] {previous_agent.stop_id} -> {self.stop_id} | "
    f"deslocamento={travel_time:.2f}s | "
    f"sinal={signal_delay:.2f}s | "
    f"embarque={boarding_time:.2f}s | "
    f"total={total_travel_time:.2f}s"
)
        # ==========================================
        # ARMAZENA
        # ==========================================

        self.travel_time_from_previous = (
            total_travel_time
        )

        # ==========================================
        # RETORNA
        # ==========================================

        return {
            "route_id": route_id,
            "previous_agent": previous_agent.stop_id,
            "current_agent": self.stop_id,
            "current_speed_kmh": current_speed,
            "free_speed_kmh": free_speed,
            "speed_kmh": estimated_speed,
            "distance_meters": distance,
            "travel_time_seconds": total_travel_time
        }
    # ==========================================
    # CALCULA O TRECHO ATÉ O AGENTE ATUAL
    # ==========================================


    def calculate_arrival_time(
        self,
        arrival_time,
        travel_time_seconds
    ):
        """
        Calcula o horário de chegada ao agente atual
        utilizando o horário recebido do agente anterior
        e o tempo estimado do trecho.
        """

        if isinstance(arrival_time, str):

            arrival_time = datetime.strptime(
                arrival_time,
                "%H:%M:%S"
            )

        arrival_time = (
            arrival_time
            + timedelta(
                seconds=travel_time_seconds
            )
        )

        return arrival_time.strftime(
            "%H:%M:%S"
        )

     # ==========================================
    # PROCESSA A VIAGEM RECEBIDA
    # ==========================================


    def process_trip(
        self,
        message,
        context
    ):
        """
        Processa uma viagem recebida do agente anterior.

        O agente:
        1. identifica a linha;
        2. identifica o horário da viagem;
        3. identifica seu agente anterior;
        4. utiliza o contexto RAW;
        5. estima a velocidade;
        6. calcula o tempo do trecho;
        7. calcula o horário de chegada;
        8. atualiza seu estado.
        """

        # ==========================================
        # CALCULA O TRECHO UTILIZANDO O CONTEXTO
        # ==========================================

        segment = self.calculate_previous_segment_from_context(
            route_id=message.route_id,
            context=context
        )

        # ==========================================
        # CALCULA HORÁRIO DE CHEGADA
        # ==========================================

        arrival_time = self.calculate_arrival_time(
            message.arrival_time,
            segment["travel_time_seconds"]
        )

        # ==========================================
        # ATUALIZA ESTADO
        # ==========================================

        self.arrival_time = arrival_time

        self.travel_time_from_previous = (
            segment["travel_time_seconds"]
        )

        self.estimated_delay = (
            message.estimated_delay
        )

        self.confidence = (
            message.confidence
        )

        # ==========================================
        # RETORNA RESULTADO
        # ==========================================

        return {
            "stop_id": self.stop_id,
            "route_id": message.route_id,
            "departure_time": message.departure_time,
            "arrival_time": arrival_time,
            "travel_time_seconds":
                segment["travel_time_seconds"],
            "current_speed_kmh":
                segment["current_speed_kmh"],
            "free_speed_kmh":
                segment["free_speed_kmh"],
            "speed_kmh":
                segment["speed_kmh"],
            "distance_meters":
                segment["distance_meters"],
            "estimated_delay":
                self.estimated_delay,
            "confidence":
                self.confidence
        }


    def get_road_speed_factor(self):
        factors = {
            "motorway": 0.95,
            "trunk": 0.90,  
            "primary": 0.85,
            "secondary": 0.90,
            "tertiary": 0.95,
            "residential": 1.00,
            "service": 1.00,
            "living_street": 0.90,
            "unknown": 1.00
        }

        return factors.get(self.road_type, 1.00)


    def get_signal_delay(self):
        delays = {
            "motorway": 0,
            "trunk": 5,
            "primary": 15,
            "secondary": 10,
            "tertiary": 5,
            "residential": 0,
            "service": 0,
            "living_street": 0,
            "unknown": 0
        }

        return delays.get(self.road_type, 0)

    def get_boarding_time(self):
        # Valor provisório: 1 passageiro por ponto
        passengers = 1
        seconds_per_passenger = 5

        return passengers * seconds_per_passenger