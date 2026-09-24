import time
from concurrent.futures import ThreadPoolExecutor

from Api.weather_api import get_weather
from Api.traffic_api import get_traffic


class ContextService:

    def __init__(self, normalizer):
        self.normalizer = normalizer

        # Últimos dados válidos das APIs por agente
        self.last_weather = {}
        self.last_traffic = {}

    # ------------------------------------------------------
    # WEATHER
    # ------------------------------------------------------

    @staticmethod
    def fetch_weather(lat, lon):
        start = time.perf_counter()

        try:
            result = get_weather(lat, lon)

            success = True
            error = None

        except Exception as e:
            result = {}
            success = False
            error = str(e)

        elapsed = time.perf_counter() - start

        return {
            "success": success,
            "data": result,
            "error": error,
            "time": elapsed
        }

    # ------------------------------------------------------
    # TRAFFIC
    # ------------------------------------------------------

    @staticmethod
    def fetch_traffic(lat, lon):
        start = time.perf_counter()

        try:
            result = get_traffic(lat, lon)

            success = True
            error = None

        except Exception as e:
            result = {}
            success = False
            error = str(e)

        elapsed = time.perf_counter() - start

        return {
            "success": success,
            "data": result,
            "error": error,
            "time": elapsed
        }

    # ------------------------------------------------------
    # CONTEXTO
    # ------------------------------------------------------

    def get_context(
        self,
        agent,
        previous_delay=0,
        previous_confidence=100
    ):

        lat = agent.latitude
        lon = agent.longitude

        context_raw = {}

        # --------------------------------------------------
        # WEATHER + TRAFFIC EM PARALELO
        # --------------------------------------------------

        start_apis = time.perf_counter()

        with ThreadPoolExecutor(max_workers=2) as executor:

            future_weather = executor.submit(
                self.fetch_weather,
                lat,
                lon
            )

            future_traffic = executor.submit(
                self.fetch_traffic,
                lat,
                lon
            )

            weather_response = future_weather.result()
            traffic_response = future_traffic.result()

        apis_time = time.perf_counter() - start_apis

        # --------------------------------------------------
        # RESULTADOS DAS APIs
        # --------------------------------------------------

        weather_result = weather_response["data"]
        traffic_result = traffic_response["data"]

        weather_time = weather_response["time"]
        traffic_time = traffic_response["time"]

        weather_ok = weather_response["success"]
        traffic_ok = traffic_response["success"]

        # --------------------------------------------------
        # TRATAMENTO DO WEATHER
        # --------------------------------------------------

        if weather_ok:

            # Guarda o último Weather válido
            self.last_weather[agent.stop_id] = weather_result

        else:

            if agent.stop_id in self.last_weather:

                weather_result = self.last_weather[
                    agent.stop_id
                ]

                print(
                    f"[AVISO] Weather indisponível em "
                    f"{agent.stop_id}. "
                    f"Usando último valor válido."
                )

            else:

                weather_result = None

                print(
                    f"[AVISO] Weather indisponível em "
                    f"{agent.stop_id}. "
                    f"Nenhum valor anterior disponível."
                )

        # --------------------------------------------------
        # TRATAMENTO DO TRAFFIC
        # --------------------------------------------------

        if traffic_ok:

            # Guarda o último Traffic válido
            self.last_traffic[agent.stop_id] = traffic_result

        else:

            if agent.stop_id in self.last_traffic:

                traffic_result = self.last_traffic[
                    agent.stop_id
                ]

                print(
                    f"[AVISO] Traffic indisponível em "
                    f"{agent.stop_id}. "
                    f"Usando último valor válido."
                )

            else:

                traffic_result = None

                print(
                    f"[AVISO] Traffic indisponível em "
                    f"{agent.stop_id}. "
                    f"Nenhum valor anterior disponível."
                )

        # --------------------------------------------------
        # ADICIONA DADOS DISPONÍVEIS AO CONTEXTO
        # --------------------------------------------------

        if weather_result is not None:
            context_raw.update(weather_result)

        if traffic_result is not None:
            context_raw.update(traffic_result)

        # --------------------------------------------------
        # STATUS DAS APIs
        # --------------------------------------------------

        context_status = {
            "weather": weather_ok,
            "traffic": traffic_ok
        }

        # --------------------------------------------------
        # TIPO DA VIA
        # --------------------------------------------------

        start_road = time.perf_counter()

        context_raw["road_type"] = agent.road_type

        road_time = time.perf_counter() - start_road

        # --------------------------------------------------
        # CONTEXTO DA PROPAGAÇÃO
        # --------------------------------------------------

        context_raw["previous_delay"] = previous_delay

        context_raw["previous_confidence"] = (
            previous_confidence
        )

        # --------------------------------------------------
        # NORMALIZAÇÃO
        # --------------------------------------------------

        start_normalization = time.perf_counter()

        normalized_result = self.normalizer.normalize(
            context_raw
        )

        normalization_time = (
            time.perf_counter()
            - start_normalization
        )

        # --------------------------------------------------
        # PERFORMANCE
        # --------------------------------------------------

        total_time = (
            apis_time
            + road_time
            + normalization_time
        )

        print("\n==============================")
        print("PERFORMANCE - CONTEXTO")
        print("==============================")
        print(f"Weather:        {weather_time:.4f} s")
        print(f"Traffic:        {traffic_time:.4f} s")
        print(f"APIs paralelas: {apis_time:.4f} s")
        print(f"Road:           {road_time:.4f} s")
        print(f"Normalização:   {normalization_time:.4f} s")
        print(f"TOTAL:          {total_time:.4f} s")
        print("==============================")

        # --------------------------------------------------
        # RETORNO
        # --------------------------------------------------

        return {
            "raw": normalized_result["raw"],
            "normalized": normalized_result["normalized"],
            "status": context_status
        }