from Agents.agent_message import AgentMessage

from Api.weather_api import get_weather
from Api.traffic_api import get_traffic
from Api.road_api import get_road_type

from Normalization.normalize import ContextNormalizer
from Fuzzy.delay_fuzzy import DelayFuzzySystem

from datetime import datetime
import time

class BusSimulation:

    def __init__(
        self,
        network,
        route_loader,
        schedule_loader
    ):

        self.network = network
        self.route_loader = route_loader
        self.schedule_loader = schedule_loader

        self.normalizer = ContextNormalizer()
        self.fuzzy = DelayFuzzySystem()

         # Estado atual da viagem
        self.current_route = None
        self.current_stop = None
        self.current_time = None
        self.previous_delay = 0.0
        self.previous_confidence = 100.0
    # ==========================================================
    # OBTÉM CONTEXTO DO AGENTE
    # ==========================================================

    def get_context(
        self,
        agent,
        previous_delay=0,
        previous_confidence=100
    ):

        lat = agent.latitude
        lon = agent.longitude

        context_raw = {}

        # ------------------------------------------------------
        # CLIMA
        # ------------------------------------------------------

        context_raw.update(
            get_weather(
                lat,
                lon
            )
        )

        # ------------------------------------------------------
        # TRÂNSITO
        # ------------------------------------------------------

        context_raw.update(
            get_traffic(
                lat,
                lon
            )
        )

        # ------------------------------------------------------
        # TIPO DA VIA
        # ------------------------------------------------------

        context_raw.update(
            get_road_type(
                lat,
                lon
            )
        )

        # ------------------------------------------------------
        # CONTEXTO DA PROPAGAÇÃO
        # ------------------------------------------------------

        context_raw["previous_delay"] = previous_delay

        context_raw["previous_confidence"] = (
            previous_confidence
        )

        # ------------------------------------------------------
        # NORMALIZAÇÃO
        # ------------------------------------------------------

        normalized_result = (
            self.normalizer.normalize(
                context_raw
            )
        )

        return {
            "raw": normalized_result["raw"],
            "normalized": normalized_result["normalized"]
        }

    # ==========================================================
    # EXECUTA FUZZY
    # ==========================================================

    def calculate_fuzzy(
        self,
        context
    ):

        return self.fuzzy.compute(
            context["normalized"]
        )

    # ==========================================================
    # SIMULA UMA VIAGEM
    # ==========================================================

    def simulate(
        self,
        route_id,
        origin_stop,
        destination_stop,
        departure_time
    ):

        # ======================================================
        # BUSCA ROTA
        # ======================================================

        route = self.route_loader.get_route(
            route_id
        )

        if not route:

            raise ValueError(
                f"Rota {route_id} não encontrada."
            )

        # ======================================================
        # OBTÉM ORDEM DOS PONTOS
        # ======================================================

        stop_ids = [
            stop["stop_id"]
            for stop in route
        ]

        # ======================================================
        # VERIFICA ORIGEM
        # ======================================================

        if origin_stop not in stop_ids:

            raise ValueError(
                f"O ponto {origin_stop} "
                f"não pertence à linha {route_id}."
            )

        # ======================================================
        # VERIFICA DESTINO
        # ======================================================

        if destination_stop not in stop_ids:

            raise ValueError(
                f"O ponto {destination_stop} "
                f"não pertence à linha {route_id}."
            )

        # ======================================================
        # POSIÇÃO DOS PONTOS
        # ======================================================

        origin_index = stop_ids.index(
            origin_stop
        )

        destination_index = stop_ids.index(
            destination_stop
        )

        # ======================================================
        # DESTINO PRECISA ESTAR À FRENTE
        # ======================================================

        if destination_index <= origin_index:

            raise ValueError(
                "O destino deve estar depois "
                "da origem na rota."
            )

        # ======================================================
        # ESTADO INICIAL DA SIMULAÇÃO
        # ======================================================

        current_stop_id = origin_stop
        current_time = departure_time

        previous_delay = 0
        previous_confidence = 100

        results = []

        # ======================================================
        # PROPAGAÇÃO
        # ======================================================

        for index in range(
            origin_index,
            destination_index
        ):

            current_stop_id = stop_ids[index]

            next_stop_id = stop_ids[index + 1]

            # --------------------------------------------------
            # AGENTES
            # --------------------------------------------------

            current_agent = self.network.get_agent(
                current_stop_id
            )

            next_agent = self.network.get_agent(
                next_stop_id
            )

            if current_agent is None:

                raise ValueError(
                    f"Agente {current_stop_id} "
                    "não encontrado na rede."
                )

            if next_agent is None:

                raise ValueError(
                    f"Agente {next_stop_id} "
                    "não encontrado na rede."
                )

            # --------------------------------------------------
            # CONTEXTO DO PRÓXIMO AGENTE
            # --------------------------------------------------

            context = self.get_context(
                next_agent,
                previous_delay=previous_delay,
                previous_confidence=previous_confidence
            )

            # --------------------------------------------------
            # FUZZY
            # --------------------------------------------------

            fuzzy_result = self.calculate_fuzzy(
                context
            )

            # --------------------------------------------------
            # MENSAGEM DA VIAGEM
            # --------------------------------------------------

            message = AgentMessage(
                source_agent=current_agent.stop_id,
                route_id=route_id,
                departure_time=current_time,
                arrival_time=current_time,
                estimated_delay=previous_delay,
                confidence=previous_confidence
            )

            # --------------------------------------------------
            # PRÓXIMO AGENTE RECEBE A MENSAGEM
            # --------------------------------------------------

            next_agent.receive_message(
                message
            )

            # --------------------------------------------------
            # PRÓXIMO AGENTE PROCESSA O TRECHO
            # --------------------------------------------------

            result_agent = next_agent.process_trip(
                message,
                context
            )

            # --------------------------------------------------
            # RESULTADO DO TRECHO
            # --------------------------------------------------

            segment_result = {

                "previous_stop":
                    current_agent.stop_id,

                "current_stop":
                    next_agent.stop_id,

                "route_id":
                    route_id,

                "departure_time":
                    current_time,

                "arrival_time":
                    result_agent["arrival_time"],

                "distance_meters":
                    result_agent["distance_meters"],

                "speed_kmh":
                    result_agent["speed_kmh"],

                "travel_time_seconds":
                    result_agent["travel_time_seconds"],

                "fuzzy_delay":
                    fuzzy_result["delay"],

                "fuzzy_delay_minutes":
                    fuzzy_result["delay_minutes"],

                "fuzzy_fallback":
                    fuzzy_result["fallback"]
            }

            results.append(
                segment_result
            )

            # --------------------------------------------------
            # AVANÇA O RELÓGIO DA SIMULAÇÃO
            # --------------------------------------------------

            current_time = (
                result_agent["arrival_time"]
            )

            # --------------------------------------------------
            # AVANÇA O ESTADO
            # --------------------------------------------------

            current_stop_id = (
                next_agent.stop_id
            )

            # --------------------------------------------------
            # PROPAGA ATRASO PARA O PRÓXIMO AGENTE
            # --------------------------------------------------

            previous_delay = (
                fuzzy_result["delay_minutes"]
            )

            previous_confidence = (
                result_agent["confidence"]
            )

        # ======================================================
        # RESULTADO FINAL
        # ======================================================

        return {
            "route_id": route_id,
            "origin": origin_stop,
            "destination": destination_stop,
            "departure_time": departure_time,
            "arrival_time": current_time,
            "segments": results
        }

    def start_trip(self, route_id, origin_stop, departure_time):
        route = self.route_loader.get_route(route_id)

        if not route:
            raise ValueError(f"Rota {route_id} não encontrada.")

        stop_ids = [stop["stop_id"] for stop in route]

        if origin_stop not in stop_ids:
            raise ValueError(
                f"O ponto {origin_stop} não pertence à linha {route_id}."
            )

        self.current_route = route_id
        self.current_stop = origin_stop
        self.current_time = departure_time
        self.previous_delay = 0.0
        self.previous_confidence = 100.0

        return {
            "route_id": self.current_route,
            "current_stop": self.current_stop,
            "current_time": self.current_time,
            "previous_delay": self.previous_delay,
            "previous_confidence": self.previous_confidence
        }

    def get_state(self):
        return {
            "route_id": self.current_route,
            "current_stop": self.current_stop,
            "current_time": self.current_time,
            "previous_delay": self.previous_delay,
            "previous_confidence": self.previous_confidence
        }
    def calculate_arrival_with_delay(
    self,
    arrival_time,
    travel_time_seconds,
    fuzzy_delay_minutes
):
        """
        Calcula o horário de chegada considerando:
        - tempo físico do trecho;
        - ajuste temporal produzido pelo sistema fuzzy.
        """

        from datetime import datetime, timedelta

        if isinstance(arrival_time, str):
            arrival_time = datetime.strptime(
                arrival_time,
                "%H:%M:%S"
            )

        total_seconds = (
            travel_time_seconds
            + (fuzzy_delay_minutes * 60)
        )

        arrival_time = (
            arrival_time
            + timedelta(seconds=total_seconds)
        )

        return arrival_time.strftime("%H:%M:%S")


    def advance(self, realtime=False):
        if self.current_route is None:
            raise ValueError("Nenhuma viagem foi iniciada.")

        route = self.route_loader.get_route(self.current_route)
        stop_ids = [stop["stop_id"] for stop in route]

        current_index = stop_ids.index(self.current_stop)

        if current_index >= len(stop_ids) - 1:
            return {
                "finished": True,
                "current_stop": self.current_stop,
                "current_time": self.current_time
            }

        current_agent = self.network.get_agent(self.current_stop)
        next_stop_id = stop_ids[current_index + 1]
        next_agent = self.network.get_agent(next_stop_id)

        if current_agent is None:
            raise ValueError(
                f"Agente não encontrado: {self.current_stop}"
            )

        if next_agent is None:
            raise ValueError(
                f"Agente não encontrado: {next_stop_id}"
            )

        # Obtém o contexto do próximo agente
        context = self.get_context(
            next_agent,
            self.previous_delay,
            self.previous_confidence
        )

        # Executa o fuzzy
        fuzzy_result = self.calculate_fuzzy(context)
        

        # Cria a mensagem entre agentes
        message = AgentMessage(
            source_agent=current_agent.stop_id,
            route_id=self.current_route,
            departure_time=self.current_time,
            arrival_time=self.current_time,
            estimated_delay=self.previous_delay,
            confidence=self.previous_confidence
        )

        # Próximo agente recebe a mensagem
        next_agent.receive_message(message)

        # Próximo agente processa a viagem
        result_agent = next_agent.process_trip(
            message,
            context
        )
        # --------------------------------------------------
        # COMBINA TEMPO DO AGENTE + FUZZY
        # --------------------------------------------------

        arrival_time = self.calculate_arrival_with_delay(
            arrival_time=message.arrival_time,
            travel_time_seconds=result_agent["travel_time_seconds"],
            fuzzy_delay_minutes=fuzzy_result["delay_minutes"]
        )

         # --------------------------------------------------
        # MODO TEMPO REAL
        # --------------------------------------------------

        if realtime:
            self.wait_until(arrival_time)

        # Atualiza o estado da simulação
        self.current_stop = next_agent.stop_id
        self.current_time = arrival_time
        self.previous_delay = fuzzy_result["delay_minutes"]
        self.previous_confidence = result_agent["confidence"]

        return {
            "finished": False,
            "previous_stop": current_agent.stop_id,
            "current_stop": self.current_stop,
            "departure_time": message.departure_time,
            "arrival_time": self.current_time,
            "distance_meters": result_agent["distance_meters"],
            "speed_kmh": result_agent["speed_kmh"],
            "travel_time_seconds": result_agent["travel_time_seconds"],
            "fuzzy_delay": fuzzy_result["delay"],
            "fuzzy_delay_minutes": fuzzy_result["delay_minutes"],
            "fuzzy_delay_seconds": fuzzy_result["delay_minutes"] * 60,
            "arrival_time": self.current_time,
        }

    def consult(
    self,
    route_id,
    destination_stop,
    origin_stop=None,
    departure_time=None
):
        route = self.route_loader.get_route(route_id)

        if not route:
            raise ValueError(f"Rota {route_id} não encontrada.")

        stop_ids = [stop["stop_id"] for stop in route]

        if destination_stop not in stop_ids:
            raise ValueError(
                f"O ponto {destination_stop} não pertence à linha {route_id}."
            )

        # Inicia uma nova viagem caso não exista uma viagem ativa
        # ou a linha seja diferente da atual.
        if self.current_route is None or self.current_route != route_id:

            if origin_stop is None or departure_time is None:
                raise ValueError(
                    "É necessário informar origin_stop e departure_time "
                    "para iniciar uma nova viagem."
                )

            self.start_trip(
                route_id=route_id,
                origin_stop=origin_stop,
                departure_time=departure_time
            )

        if self.current_stop not in stop_ids:
            raise ValueError(
                f"O ponto atual {self.current_stop} não pertence "
                f"à linha {route_id}."
            )

        current_index = stop_ids.index(self.current_stop)
        destination_index = stop_ids.index(destination_stop)

        if destination_index < current_index:
            raise ValueError(
                "O destino deve estar depois ou ser o ponto atual da viagem."
            )

        starting_stop = self.current_stop
        starting_time = self.current_time

        segments = []

        while self.current_stop != destination_stop:

            step = self.advance()

            if step["finished"]:
                break

            segments.append(step)

        return {
            "route_id": self.current_route,
            "origin": starting_stop,
            "destination": destination_stop,
            "departure_time": starting_time,
            "arrival_time": self.current_time,
            "segments": segments,
            "current_stop": self.current_stop
        }

    def wait_until(self, target_time):
        """
        Aguarda até o relógio real atingir o horário previsto.

        O horário previsto é tratado como o horário real
        de chegada ao próximo ponto.
        """

        if isinstance(target_time, str):
            target_time = datetime.strptime(
                target_time,
                "%H:%M:%S"
            )

        now = datetime.now()

        target_datetime = now.replace(
            hour=target_time.hour,
            minute=target_time.minute,
            second=target_time.second,
            microsecond=0
        )

        # Caso o horário previsto já tenha passado hoje,
        # não há necessidade de esperar.
        if target_datetime <= now:
            return

        print(
            f"\nAguardando chegada em "
            f"{target_datetime.strftime('%H:%M:%S')}..."
        )

        while datetime.now() < target_datetime:
            time.sleep(1)

    def run_realtime(
        self,
        route_id,
        origin_stop,
        destination_stop,
        departure_time
    ):
        """
        Executa a viagem acompanhando o relógio real.

        Cada ponto previsto é considerado concretizado quando
        o relógio real atinge seu horário.

        Após a concretização de um ponto:
        - o passado é congelado;
        - o ponto concretizado passa a ser a nova referência;
        - o futuro até o destino é recalculado.
        """

        # ==========================================================
        # INICIA A VIAGEM
        # ==========================================================

        self.start_trip(
            route_id=route_id,
            origin_stop=origin_stop,
            departure_time=departure_time
        )

        # ==========================================================
        # BUSCA ROTA
        # ==========================================================

        route = self.route_loader.get_route(
            route_id
        )

        if not route:
            raise ValueError(
                f"Rota {route_id} não encontrada."
            )

        stop_ids = [
            stop["stop_id"]
            for stop in route
        ]

        # ==========================================================
        # VERIFICA DESTINO
        # ==========================================================

        if destination_stop not in stop_ids:
            raise ValueError(
                f"O ponto {destination_stop} "
                f"não pertence à linha {route_id}."
            )

        destination_index = stop_ids.index(
            destination_stop
        )

        current_index = stop_ids.index(
            self.current_stop
        )

        if destination_index <= current_index:
            raise ValueError(
                "O destino deve estar depois da origem."
            )

        # ==========================================================
        # RESULTADOS
        # ==========================================================

        results = []

        print("\n========================================")
        print("      SIMULAÇÃO EM TEMPO REAL")
        print("========================================")

        print(
            f"Origem: {self.current_stop}"
        )

        print(
            f"Horário inicial: {self.current_time}"
        )

        print(
            f"Destino: {destination_stop}"
        )

        # ==========================================================
        # EXECUÇÃO DA VIAGEM
        # ==========================================================

        while self.current_stop != destination_stop:

            # ------------------------------------------------------
            # CALCULA O PRÓXIMO TRECHO
            # ------------------------------------------------------

            step = self.advance(
                realtime=True
            )

            results.append(
                step
            )

            # ------------------------------------------------------
            # PONTO CONCRETIZADO
            # ------------------------------------------------------

            print(
                f"\nChegada confirmada: "
                f"{step['current_stop']} "
                f"às {step['arrival_time']}"
            )

            # ------------------------------------------------------
            # VERIFICA SE CHEGOU AO DESTINO
            # ------------------------------------------------------

            if step["current_stop"] == destination_stop:

                break

            # ------------------------------------------------------
            # NOVO PONTO DE REFERÊNCIA
            # ------------------------------------------------------

            print(
                f"Novo ponto de referência: "
                f"{self.current_stop}"
            )

            # ------------------------------------------------------
            # RECALCULA TODO O FUTURO
            # ------------------------------------------------------

            print(
                "\nRecalculando previsão "
                "dos próximos pontos..."
            )

            future = self.calculate_future(
                destination_stop=destination_stop
            )

            # ------------------------------------------------------
            # MOSTRA NOVA PREVISÃO
            # ------------------------------------------------------

            print(
                "\n========================================"
            )

            print(
                "       NOVA PREVISÃO DO FUTURO"
            )

            print(
                "========================================"
            )

            for prediction in future:

                print(
                    f"{prediction['previous_stop']} → "
                    f"{prediction['current_stop']} | "
                    f"Saída: "
                    f"{prediction['departure_time']} | "
                    f"Chegada: "
                    f"{prediction['arrival_time']} | "
                    f"Fuzzy: "
                    f"{prediction['fuzzy_delay_minutes']:+.2f} min"
                )

            print(
                "\nAguardando próxima concretização..."
            )

            # ------------------------------------------------------
            # IMPORTANTE:
            #
            # advance() no próximo ciclo irá recalcular
            # novamente o próximo trecho a partir do estado
            # concretizado.
            # ------------------------------------------------------

        # ==========================================================
        # FINALIZAÇÃO
        # ==========================================================

        print("\n========================================")
        print("        VIAGEM FINALIZADA")
        print("========================================")

        print(
            f"Chegada ao destino: "
            f"{self.current_time}"
        )

        return {
            "route_id": self.current_route,
            "origin": origin_stop,
            "destination": destination_stop,
            "departure_time": departure_time,
            "arrival_time": self.current_time,
            "segments": results,
            "current_stop": self.current_stop
        }
    
    def calculate_future(
    self,
    destination_stop
):
        route = self.route_loader.get_route(
            self.current_route
        )

        stop_ids = [
            stop["stop_id"]
            for stop in route
        ]

        current_index = stop_ids.index(
            self.current_stop
        )

        destination_index = stop_ids.index(
            destination_stop
        )

        if destination_index <= current_index:
            return []

        current_stop_id = self.current_stop
        current_time = self.current_time

        previous_delay = self.previous_delay
        previous_confidence = self.previous_confidence

        predictions = []

        for index in range(
            current_index,
            destination_index
        ):

            current_stop_id = stop_ids[index]
            next_stop_id = stop_ids[index + 1]

            current_agent = self.network.get_agent(
                current_stop_id
            )

            next_agent = self.network.get_agent(
                next_stop_id
            )

            if current_agent is None:
                raise ValueError(
                    f"Agente {current_stop_id} não encontrado."
                )

            if next_agent is None:
                raise ValueError(
                    f"Agente {next_stop_id} não encontrado."
                )

            # ==================================================
            # NOVO CONTEXTO
            # ==================================================

            context = self.get_context(
                next_agent,
                previous_delay,
                previous_confidence
            )

            # ==================================================
            # NOVO FUZZY
            # ==================================================

            fuzzy_result = self.calculate_fuzzy(
                context
            )

            # ==================================================
            # TEMPO DO TRECHO
            # ==================================================

            message = AgentMessage(
                source_agent=current_agent.stop_id,
                route_id=self.current_route,
                departure_time=current_time,
                arrival_time=current_time,
                estimated_delay=previous_delay,
                confidence=previous_confidence
            )

            next_agent.receive_message(message)

            result_agent = next_agent.process_trip(
                message,
                context
            )

            # ==================================================
            # NOVA PREVISÃO DE CHEGADA
            # ==================================================

            arrival_time = self.calculate_arrival_with_delay(
                arrival_time=current_time,
                travel_time_seconds=result_agent[
                    "travel_time_seconds"
                ],
                fuzzy_delay_minutes=fuzzy_result[
                    "delay_minutes"
                ]
            )

            predictions.append({
                "previous_stop": current_agent.stop_id,
                "current_stop": next_agent.stop_id,
                "departure_time": current_time,
                "arrival_time": arrival_time,
                "distance_meters": result_agent[
                    "distance_meters"
                ],
                "speed_kmh": result_agent[
                    "speed_kmh"
                ],
                "travel_time_seconds": result_agent[
                    "travel_time_seconds"
                ],
                "fuzzy_delay": fuzzy_result[
                    "delay"
                ],
                "fuzzy_delay_minutes": fuzzy_result[
                    "delay_minutes"
                ],
                "fuzzy_fallback": fuzzy_result[
                    "fallback"
                ],
                "confidence": result_agent[
                    "confidence"
                ]
            })

            # ==================================================
            # PRÓXIMO TRECHO
            # ==================================================

            current_time = arrival_time
            current_stop_id = next_agent.stop_id

            previous_delay = fuzzy_result[
                "delay_minutes"
            ]

            previous_confidence = result_agent[
                "confidence"
            ]

        return predictions