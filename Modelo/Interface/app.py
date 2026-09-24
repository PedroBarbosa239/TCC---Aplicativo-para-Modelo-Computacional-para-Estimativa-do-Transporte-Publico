import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta

from Agents.agent_network import AgentNetwork
from Data.stop_loader import StopLoader
from Data.route_loader import RouteLoader
from Schedules.schedule_loader import ScheduleLoader
from Simulation.bus_simulation import BusSimulation
from Services.simulation_worker import SimulationWorker
from Services.simulation_state import SimulationState

from tkintermapview import TkinterMapView

from Api.routing_api import get_route


# ==========================================================
# CONFIGURAÇÃO DOS ARQUIVOS
# ==========================================================

STOPS_FILE = "Data/stops.csv"
ROUTES_FILE = "Data/routes.csv"
SCHEDULE_FILE = "Data/schedules.csv"


# ==========================================================
# CARREGAMENTO DO MODELO
# ==========================================================

stop_loader = StopLoader(STOPS_FILE)
stop_loader.load()

agents = stop_loader.create_agents()

network = AgentNetwork()
network.add_agents(agents)

route_loader = RouteLoader(ROUTES_FILE)
route_loader.load()

network.connect_routes_from_loader(
    route_loader
)

schedule_loader = ScheduleLoader(
    SCHEDULE_FILE
)
schedule_loader.load()

simulation = BusSimulation(
    network=network,
    route_loader=route_loader,
    schedule_loader=schedule_loader
)


# ==========================================================
# INTERFACE
# ==========================================================

class BusSimulationApp:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "Modelo de Estimativa de Transporte Público"
        )

        self.root.geometry(
            "1200x700"
        )

        # ==================================================
        # MODELO
        # ==================================================

        self.simulation = simulation

        # ==================================================
        # WORKER
        # ==================================================

        self.worker = SimulationWorker(
            self.simulation
        )

        self.worker.start()

        # ==================================================
        # ESTADO DA INTERFACE
        # ==================================================

        self.state = SimulationState.IDLE

        self.next_prediction = None

        self.destination_stop = None

        self.trip_running = False

        # ==================================================
        # ESTADO DO MAPA
        # ==================================================

        # Linha completa visual da rota
        self.route_path = None

        # Marcadores dos pontos
        self.stop_markers = []

        # Marcador do ônibus
        self.current_bus_marker = None

        # Geometria OSRM separada por trecho
        #
        # Exemplo:
        #
        # legs[0] = P1 -> P2
        # legs[1] = P2 -> P3
        # legs[2] = P3 -> P4
        #
        self.route_geometry_legs = []

        # ID do after() responsável pela animação
        self.bus_animation_job = None

        # Previsão que está sendo representada atualmente
        self.active_bus_prediction = None

        # ==================================================
        # INTERFACE
        # ==================================================

        self.create_widgets()

        self.load_routes()

    # ======================================================
    # ESTADO
    # ======================================================

    def set_state(self, state):

        self.state = state

        state_messages = {

            SimulationState.IDLE:
                "Sistema aguardando viagem...",

            SimulationState.RUNNING:
                "Viagem em andamento...",

            SimulationState.WAITING_ARRIVAL:
                "Aguardando chegada ao próximo ponto...",

            SimulationState.FINISHED:
                "Viagem finalizada.",

            SimulationState.ERROR:
                "Erro durante a simulação.",

            SimulationState.STOPPED:
                "Viagem interrompida."
        }

        self.state_label.config(
            text=state_messages.get(
                state,
                "Estado desconhecido."
            )
        )

    # ======================================================
    # WIDGETS
    # ======================================================

    def create_widgets(self):

        # ==================================================
        # LAYOUT PRINCIPAL
        # ==================================================

        main_frame = ttk.Frame(
            self.root
        )

        main_frame.pack(
            fill="both",
            expand=True
        )

        # ==================================================
        # PAINEL ESQUERDO
        # ==================================================

        left_frame = ttk.Frame(
            main_frame,
            width=400
        )

        left_frame.pack(
            side="left",
            fill="y",
            padx=10,
            pady=10
        )

        left_frame.pack_propagate(
            False
        )

        # ==================================================
        # PAINEL DIREITO / MAPA
        # ==================================================

        right_frame = ttk.Frame(
            main_frame
        )

        right_frame.pack(
            side="right",
            fill="both",
            expand=True,
            padx=(0, 10),
            pady=10
        )

        # ==================================================
        # TÍTULO
        # ==================================================

        title = ttk.Label(
            left_frame,
            text=(
                "MODELO DE ESTIMATIVA DE "
                "TRANSPORTE PÚBLICO"
            ),
            font=(
                "Arial",
                16,
                "bold"
            ),
            wraplength=370,
            justify="center"
        )

        title.pack(
            pady=15
        )

        # ==================================================
        # CONFIGURAÇÃO
        # ==================================================

        config_frame = ttk.LabelFrame(
            left_frame,
            text="Configuração da viagem",
            padding=15
        )

        config_frame.pack(
            fill="x"
        )

        # ==================================================
        # ROTA
        # ==================================================

        ttk.Label(
            config_frame,
            text="Rota:"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )

        self.route_combo = ttk.Combobox(
            config_frame,
            state="readonly",
            width=30
        )

        self.route_combo.grid(
            row=0,
            column=1,
            padx=5,
            pady=5
        )

        self.route_combo.bind(
            "<<ComboboxSelected>>",
            self.route_selected
        )

        # ==================================================
        # ORIGEM
        # ==================================================

        ttk.Label(
            config_frame,
            text="Origem:"
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )

        self.origin_combo = ttk.Combobox(
            config_frame,
            state="readonly",
            width=30
        )

        self.origin_combo.grid(
            row=1,
            column=1,
            padx=5,
            pady=5
        )

        # ==================================================
        # DESTINO
        # ==================================================

        ttk.Label(
            config_frame,
            text="Destino:"
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )

        self.destination_combo = ttk.Combobox(
            config_frame,
            state="readonly",
            width=30
        )

        self.destination_combo.grid(
            row=2,
            column=1,
            padx=5,
            pady=5
        )

        # ==================================================
        # HORÁRIO
        # ==================================================

        ttk.Label(
            config_frame,
            text="Horário de partida:"
        ).grid(
            row=3,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )

        self.time_entry = ttk.Entry(
            config_frame,
            width=33
        )

        self.time_entry.grid(
            row=3,
            column=1,
            padx=5,
            pady=5
        )

        self.time_entry.insert(
            0,
            (
                datetime.now()
                + timedelta(seconds=10)
            ).strftime("%H:%M:%S")
        )

        # ==================================================
        # BOTÃO
        # ==================================================

        self.start_button = ttk.Button(
            config_frame,
            text="INICIAR VIAGEM",
            command=self.start_trip
        )

        self.start_button.grid(
            row=4,
            column=0,
            columnspan=2,
            pady=15
        )

        # ==================================================
        # ESTADO ATUAL
        # ==================================================

        state_frame = ttk.LabelFrame(
            left_frame,
            text="Estado atual",
            padding=15
        )

        state_frame.pack(
            fill="x",
            pady=15
        )

        self.state_label = ttk.Label(
            state_frame,
            text="Sistema aguardando viagem..."
        )

        self.state_label.pack(
            anchor="w"
        )

        # ==================================================
        # PREVISÃO
        # ==================================================

        prediction_frame = ttk.LabelFrame(
            left_frame,
            text="Previsão",
            padding=10
        )

        prediction_frame.pack(
            fill="both",
            expand=True
        )

        self.prediction_text = tk.Text(
            prediction_frame,
            height=12,
            state="disabled"
        )

        self.prediction_text.pack(
            fill="both",
            expand=True
        )

        # ==================================================
        # MAPA
        # ==================================================

        self.map_widget = TkinterMapView(
            right_frame,
            corner_radius=0
        )

        self.map_widget.pack(
            fill="both",
            expand=True
        )

        # ==================================================
        # POSIÇÃO INICIAL
        # ==================================================

        self.map_widget.set_position(
            -22.2231,
            -54.8120
        )

        self.map_widget.set_zoom(
            15
        )

    # ======================================================
    # CARREGA ROTAS
    # ======================================================

    def load_routes(self):

        routes = route_loader.get_route_ids()

        self.route_combo["values"] = routes

        if routes:

            self.route_combo.current(0)

            self.route_selected()

    # ======================================================
    # ROTA SELECIONADA
    # ======================================================

    def route_selected(self, event=None):

        route_id = self.route_combo.get()

        if not route_id:
            return

        route = route_loader.get_route(
            route_id
        )

        stop_ids = [
            stop["stop_id"]
            for stop in route
        ]

        self.origin_combo["values"] = stop_ids

        self.destination_combo["values"] = stop_ids

        if len(stop_ids) >= 2:

            self.origin_combo.current(0)

            self.destination_combo.current(1)

        self.update_map_route(
            route
        )

    # ======================================================
    # ATUALIZA MAPA DA ROTA
    # ======================================================

    def update_map_route(self, route):

        # ==================================================
        # CANCELA ANIMAÇÃO ANTERIOR
        # ==================================================

        self.cancel_bus_animation()

        # ==================================================
        # LIMPA MARCADORES
        # ==================================================

        for marker in self.stop_markers:

            try:
                marker.delete()
            except Exception:
                pass

        self.stop_markers = []

        # ==================================================
        # LIMPA ÔNIBUS
        # ==================================================

        self.remove_bus_marker()

        # ==================================================
        # LIMPA ROTA VISUAL
        # ==================================================

        if self.route_path is not None:

            try:
                self.route_path.delete()
            except Exception:
                pass

            self.route_path = None

        # ==================================================
        # LIMPA GEOMETRIAS
        # ==================================================

        self.route_geometry_legs = []

        self.active_bus_prediction = None

        # ==================================================
        # SEM ROTA
        # ==================================================

        if not route:
            return

        # ==================================================
        # COORDENADAS DOS PONTOS
        # ==================================================

        coordinates = []

        for item in route:

            stop = stop_loader.get_stop(
                item["stop_id"]
            )

            if stop is None:
                continue

            latitude = stop["latitude"]

            longitude = stop["longitude"]

            coordinates.append(
                (
                    latitude,
                    longitude
                )
            )

            # ----------------------------------------------
            # MARCADOR
            # ----------------------------------------------

            marker = self.map_widget.set_marker(
                latitude,
                longitude,
                text=item["stop_id"]
            )

            self.stop_markers.append(
                marker
            )

        if len(coordinates) < 2:
            return

        # ==================================================
        # CENTRALIZA
        # ==================================================

        middle = coordinates[
            len(coordinates) // 2
        ]

        self.map_widget.set_position(
            middle[0],
            middle[1]
        )

        self.map_widget.set_zoom(
            15
        )

        # ==================================================
        # OSRM
        # ==================================================

        try:

            osrm_route = get_route(
                coordinates
            )

            self.route_geometry_legs = (
                osrm_route.get(
                    "legs_geometry",
                    []
                )
            )

            geometry = osrm_route.get(
                "geometry",
                []
            )

            if geometry:

                self.route_path = (
                    self.map_widget.set_path(
                        geometry
                    )
                )

        except Exception as e:

            print(
                f"Erro ao carregar rota no mapa: {e}"
            )

            # ----------------------------------------------
            # FALLBACK VISUAL
            # ----------------------------------------------

            self.route_geometry_legs = []

            self.route_path = (
                self.map_widget.set_path(
                    coordinates
                )
            )

    # ======================================================
    # INICIA VIAGEM
    # ======================================================

    def start_trip(self):

        # ==================================================
        # VALORES
        # ==================================================

        route_id = self.route_combo.get()

        origin = self.origin_combo.get()

        destination = (
            self.destination_combo.get()
        )

        departure_time = (
            self.time_entry.get().strip()
        )

        # ==================================================
        # VALIDAÇÕES
        # ==================================================

        if not route_id:

            messagebox.showerror(
                "Erro",
                "Selecione uma rota."
            )

            return

        if not origin:

            messagebox.showerror(
                "Erro",
                "Selecione a origem."
            )

            return

        if not destination:

            messagebox.showerror(
                "Erro",
                "Selecione o destino."
            )

            return

        if origin == destination:

            messagebox.showerror(
                "Erro",
                "Origem e destino devem ser diferentes."
            )

            return

        try:

            datetime.strptime(
                departure_time,
                "%H:%M:%S"
            )

        except ValueError:

            messagebox.showerror(
                "Erro",
                "Informe o horário no formato HH:MM:SS."
            )

            return

        # ==================================================
        # CANCELA ESTADO ANTERIOR
        # ==================================================

        self.cancel_bus_animation()

        self.remove_bus_marker()

        self.next_prediction = None

        self.active_bus_prediction = None

        # ==================================================
        # INICIA MODELO
        # ==================================================

        try:

            self.simulation.start_trip(
                route_id=route_id,
                origin_stop=origin,
                departure_time=departure_time
            )

        except Exception as e:

            self.set_state(
                SimulationState.ERROR
            )

            messagebox.showerror(
                "Erro ao iniciar viagem",
                str(e)
            )

            return

        # ==================================================
        # ESTADO
        # ==================================================

        self.trip_running = True

        self.destination_stop = destination

        self.set_state(
            SimulationState.RUNNING
        )

        # ==================================================
        # POSICIONA ÔNIBUS NA ORIGEM
        # ==================================================

        self.place_bus_at_stop(
            origin
        )

        # ==================================================
        # LIMPA PREVISÃO
        # ==================================================

        self.prediction_text.config(
            state="normal"
        )

        self.prediction_text.delete(
            "1.0",
            tk.END
        )

        self.prediction_text.insert(
            tk.END,
            "VIAGEM INICIADA\n"
            "==============================\n"
            f"Rota: {route_id}\n"
            f"Origem: {origin}\n"
            f"Destino: {destination}\n"
            f"Partida: {departure_time}\n\n"
        )

        self.prediction_text.config(
            state="disabled"
        )

        self.update_state()

        # ==================================================
        # CALCULA PRIMEIRO SEGMENTO
        # ==================================================

        self.process_next_segment()

    # ======================================================
    # PROCESSA PRÓXIMO SEGMENTO
    # ======================================================

    def process_next_segment(self):

        if self.state != SimulationState.RUNNING:

            return

        state = self.simulation.get_state()

        current_stop = state[
            "current_stop"
        ]

        # ==================================================
        # JÁ CHEGOU
        # ==================================================

        if current_stop == self.destination_stop:

            self.finish_trip()

            return

        # ==================================================
        # SOLICITA PREVISÃO
        # ==================================================

        self.worker.submit(
            self.simulation.calculate_next_prediction,
            self.destination_stop
        )

        self.check_worker_result()

    # ======================================================
    # RESULTADO DO WORKER
    # ======================================================

    def check_worker_result(self):

        if self.state != SimulationState.RUNNING:

            return

        result = self.worker.get_result()

        # ==================================================
        # AINDA PROCESSANDO
        # ==================================================

        if result is None:

            self.root.after(
                100,
                self.check_worker_result
            )

            return

        # ==================================================
        # ERRO
        # ==================================================

        if not result["success"]:

            self.set_state(
                SimulationState.ERROR
            )

            messagebox.showerror(
                "Erro na previsão",
                str(result["error"])
            )

            return

        # ==================================================
        # PREVISÃO
        # ==================================================

        result_prediction = result["result"]

        if result_prediction is None:

            self.set_state(
                SimulationState.ERROR
            )

            self.add_prediction_text(
                "\nNenhuma previsão disponível.\n"
            )

            return

        # ==================================================
        # NOVO FORMATO DA PREVISÃO
        #
        # O modelo agora retorna:
        #
        # next_prediction       -> próximo trecho
        # destination_prediction -> previsão até o destino
        # future_predictions    -> todos os trechos futuros
        #
        # A interface usa apenas os dois primeiros aqui.
        # ==================================================

        prediction = result_prediction[
            "next_prediction"
        ]

        destination_prediction = result_prediction[
            "destination_prediction"
        ]

        # ==================================================
        # GUARDA PREVISÃO DO PRÓXIMO TRECHO
        # ==================================================

        self.next_prediction = prediction

        self.active_bus_prediction = prediction

        current_stop = (
            prediction["previous_stop"]
        )

        next_stop = (
            prediction["current_stop"]
        )

        departure_time = (
            prediction["departure_time"]
        )

        arrival_time = (
            prediction["arrival_time"]
        )

        # ==================================================
        # MOSTRA PREVISÃO DO DESTINO
        # ==================================================

        self.add_prediction_text(

            "\n================================\n"
            "       PREVISÃO DO DESTINO\n"
            "================================\n"

            f"Referência atual: "
            f"{destination_prediction['current_stop']}\n"

            f"Destino: "
            f"{destination_prediction['destination_stop']}\n"

            f"Previsão de chegada ao destino: "
            f"{destination_prediction['arrival_time']}\n"
        )

        # ==================================================
        # MOSTRA PREVISÃO DO PRÓXIMO TRECHO
        # ==================================================

        self.add_prediction_text(

            "\n--------------------------------\n"
            "       PRÓXIMO TRECHO\n"
            "--------------------------------\n"

            f"REFERÊNCIA ATUAL: "
            f"{current_stop}\n"

            f"PRÓXIMO PONTO: "
            f"{next_stop}\n"

            f"SAÍDA DO TRECHO: "
            f"{departure_time}\n"

            f"PREVISÃO DE CHEGADA: "
            f"{arrival_time}\n"

            f"Tempo do trecho: "
            f"{prediction['travel_time_seconds']:.2f} s\n"

            f"Atraso fuzzy: "
            f"{prediction['fuzzy_delay']:.2f}\n"

            f"Atraso temporal: "
            f"{prediction['fuzzy_delay_minutes']:+.2f} min\n"
        )

        self.update_state()

        # ==================================================
        # IMPORTANTE:
        #
        # AQUI O MAPA NÃO "DECIDE" O TEMPO.
        #
        # Ele recebe exatamente essa previsão.
        #
        # A animação representa SOMENTE:
        #
        # current_stop -> next_stop
        #
        # ==================================================

        self.start_map_segment(
            prediction
        )

        # ==================================================
        # MODELO AGORA AGUARDA A CHEGADA
        # ==================================================

        self.set_state(
            SimulationState.WAITING_ARRIVAL
        )

        self.check_arrival()

    # ======================================================
    # INICIA ANIMAÇÃO DO SEGMENTO
    # ======================================================

    def start_map_segment(self, prediction):

        if prediction is None:

            return

        # ----------------------------------------------
        # CANCELA QUALQUER ANIMAÇÃO ANTIGA
        # ----------------------------------------------

        self.cancel_bus_animation()

        # ----------------------------------------------
        # GUARDA SEGMENTO ATUAL
        # ----------------------------------------------

        self.active_bus_prediction = (
            prediction
        )

        # ----------------------------------------------
        # ANIMA SOMENTE ESTE SEGMENTO
        # ----------------------------------------------

        self.animate_bus(
            prediction
        )

    # ======================================================
    # ANIMA ÔNIBUS
    # ======================================================

    def animate_bus(self, prediction):

        if prediction is None:

            return

        previous_stop = (
            prediction["previous_stop"]
        )

        current_stop = (
            prediction["current_stop"]
        )

        departure_time = (
            prediction["departure_time"]
        )

        arrival_time = (
            prediction["arrival_time"]
        )

        # ==================================================
        # ROTA ATUAL
        # ==================================================

        route_id = self.route_combo.get()

        route = route_loader.get_route(
            route_id
        )

        if not route:

            return

        stop_ids = [
            stop["stop_id"]
            for stop in route
        ]

        # ==================================================
        # ÍNDICE DO SEGMENTO
        # ==================================================

        try:

            segment_index = stop_ids.index(
                previous_stop
            )

        except ValueError:

            print(
                "Não foi possível localizar "
                f"{previous_stop} na rota."
            )

            return

        # ==================================================
        # VALIDA DESTINO DO SEGMENTO
        # ==================================================

        if segment_index + 1 >= len(
            stop_ids
        ):

            print(
                "Segmento inválido."
            )

            return

        expected_next_stop = (
            stop_ids[
                segment_index + 1
            ]
        )

        if expected_next_stop != current_stop:

            print(
                "A previsão não corresponde "
                "ao próximo ponto da rota."
            )

            return

        # ==================================================
        # GEOMETRIA OSRM DO SEGMENTO
        # ==================================================

        if segment_index >= len(
            self.route_geometry_legs
        ):

            print(
                "Geometria OSRM do segmento "
                "não encontrada."
            )

            # Ainda podemos manter o ônibus
            # visualmente no ponto atual.

            self.place_bus_at_stop(
                previous_stop
            )

            return

        geometry = (
            self.route_geometry_legs[
                segment_index
            ]
        )

        if not geometry:

            self.place_bus_at_stop(
                previous_stop
            )

            return

        # ==================================================
        # HORÁRIOS
        # ==================================================

        try:

            departure = datetime.strptime(
                departure_time,
                "%H:%M:%S"
            )

            arrival = datetime.strptime(
                arrival_time,
                "%H:%M:%S"
            )

        except ValueError:

            print(
                "Erro ao interpretar "
                "horário da animação."
            )

            return

        # ==================================================
        # COLOCA NO DIA ATUAL
        # ==================================================

        now = datetime.now()

        departure = departure.replace(
            year=now.year,
            month=now.month,
            day=now.day
        )

        arrival = arrival.replace(
            year=now.year,
            month=now.month,
            day=now.day
        )

        # ==================================================
        # TRATAMENTO DE VIRADA DE DIA
        # ==================================================

        if arrival < departure:

            arrival += timedelta(
                days=1
            )

        # ==================================================
        # DURAÇÃO EXATA DO SEGMENTO
        # ==================================================

        total_seconds = (
            arrival - departure
        ).total_seconds()

        if total_seconds <= 0:

            total_seconds = 0.1

        # ==================================================
        # POSIÇÃO INICIAL
        # ==================================================

        first_latitude, first_longitude = (
            geometry[0]
        )

        self.set_bus_position(
            first_latitude,
            first_longitude
        )

        # ==================================================
        # ANIMAÇÃO
        # ==================================================

        def update_position():

            # ------------------------------------------
            # SE A VIAGEM FOI CANCELADA
            # ------------------------------------------

            if not self.trip_running:

                self.bus_animation_job = None

                return

            # ------------------------------------------
            # GARANTE QUE A PREVISÃO AINDA É A ATIVA
            # ------------------------------------------

            if (
                self.active_bus_prediction
                is not prediction
            ):

                self.bus_animation_job = None

                return

            current_time = datetime.now()

            # ------------------------------------------
            # TEMPO DECORRIDO
            # ------------------------------------------

            elapsed = (
                current_time - departure
            ).total_seconds()

            # ------------------------------------------
            # AINDA NÃO É HORA DE PARTIR
            # ------------------------------------------

            if elapsed < 0:

                self.set_bus_position(
                    first_latitude,
                    first_longitude
                )

                self.bus_animation_job = (
                    self.root.after(
                        100,
                        update_position
                    )
                )

                return

            # ------------------------------------------
            # PROGRESSO DO SEGMENTO
            # ------------------------------------------

            progress = (
                elapsed
                / total_seconds
            )

            progress = max(
                0.0,
                min(
                    1.0,
                    progress
                )
            )

            # ------------------------------------------
            # POSIÇÃO NA GEOMETRIA OSRM
            # ------------------------------------------

            latitude, longitude = (
                self.position_on_geometry(
                    geometry,
                    progress
                )
            )

            self.set_bus_position(
                latitude,
                longitude
            )

            # ------------------------------------------
            # SEGMENTO AINDA NÃO TERMINOU
            # ------------------------------------------

            if progress < 1.0:

                self.bus_animation_job = (
                    self.root.after(
                        100,
                        update_position
                    )
                )

                return

            # ------------------------------------------
            # SEGMENTO TERMINOU
            # ------------------------------------------

            final_latitude, final_longitude = (
                geometry[-1]
            )

            self.set_bus_position(
                final_latitude,
                final_longitude
            )

            self.bus_animation_job = None

        # ==================================================
        # INICIA
        # ==================================================

        update_position()

    # ======================================================
    # POSIÇÃO AO LONGO DA GEOMETRIA
    # ======================================================

    def position_on_geometry(
        self,
        geometry,
        progress
    ):

        if not geometry:

            return None, None

        if len(geometry) == 1:

            return geometry[0]

        # --------------------------------------------------
        # IMPORTANTE:
        #
        # Não usamos:
        #
        # P1 -> P2 em linha reta
        #
        # Usamos os pontos reais fornecidos pelo OSRM.
        # --------------------------------------------------

        position = (
            progress
            * (len(geometry) - 1)
        )

        index = int(
            position
        )

        if index >= len(geometry) - 1:

            return geometry[-1]

        local_progress = (
            position - index
        )

        lat1, lon1 = geometry[
            index
        ]

        lat2, lon2 = geometry[
            index + 1
        ]

        latitude = (
            lat1
            + (
                lat2 - lat1
            )
            * local_progress
        )

        longitude = (
            lon1
            + (
                lon2 - lon1
            )
            * local_progress
        )

        return latitude, longitude

    # ======================================================
    # POSICIONA ÔNIBUS
    # ======================================================

    def set_bus_position(
        self,
        latitude,
        longitude
    ):

        if self.current_bus_marker is None:

            self.current_bus_marker = (
                self.map_widget.set_marker(
                    latitude,
                    longitude,
                    text="🚌"
                )
            )

            return

        try:

            self.current_bus_marker.set_position(
                latitude,
                longitude
            )

        except Exception:

            # Fallback caso a versão do
            # tkintermapview não suporte
            # set_position no marcador.

            try:
                self.current_bus_marker.delete()
            except Exception:
                pass

            self.current_bus_marker = (
                self.map_widget.set_marker(
                    latitude,
                    longitude,
                    text="🚌"
                )
            )

    # ======================================================
    # POSICIONA NO PONTO
    # ======================================================

    def place_bus_at_stop(
        self,
        stop_id
    ):

        stop = stop_loader.get_stop(
            stop_id
        )

        if stop is None:

            return

        self.set_bus_position(
            stop["latitude"],
            stop["longitude"]
        )

    # ======================================================
    # CANCELA ANIMAÇÃO
    # ======================================================

    def cancel_bus_animation(self):

        if self.bus_animation_job is None:

            return

        try:

            self.root.after_cancel(
                self.bus_animation_job
            )

        except Exception:
            pass

        self.bus_animation_job = None

    # ======================================================
    # REMOVE ÔNIBUS
    # ======================================================

    def remove_bus_marker(self):

        if self.current_bus_marker is None:

            return

        try:

            self.current_bus_marker.delete()

        except Exception:
            pass

        self.current_bus_marker = None

    # ======================================================
    # VERIFICA CHEGADA
    # ======================================================

    def check_arrival(self):

        if self.state != (
            SimulationState.WAITING_ARRIVAL
        ):

            return

        if self.next_prediction is None:

            return

        arrival_time = (
            self.next_prediction[
                "arrival_time"
            ]
        )

        try:

            target_time = datetime.strptime(
                arrival_time,
                "%H:%M:%S"
            )

        except ValueError:

            self.set_state(
                SimulationState.ERROR
            )

            self.add_prediction_text(
                "\nErro ao interpretar "
                "o horário previsto.\n"
            )

            return

        now = datetime.now()

        target_time = target_time.replace(
            year=now.year,
            month=now.month,
            day=now.day
        )

        # ==================================================
        # VIRADA DE DIA
        # ==================================================

        if target_time < now:

            # Se a diferença for muito grande,
            # provavelmente é uma previsão do
            # próximo dia.

            if (
                now - target_time
            ).total_seconds() > 12 * 3600:

                target_time += timedelta(
                    days=1
                )

        # ==================================================
        # AINDA NÃO CHEGOU
        # ==================================================

        if now < target_time:

            self.root.after(
                200,
                self.check_arrival
            )

            return

        # ==================================================
        # CHEGOU
        # ==================================================

        self.concretize_arrival()

    # ======================================================
    # CONCRETIZA CHEGADA
    # ======================================================

    def concretize_arrival(self):

        prediction = (
            self.next_prediction
        )

        if prediction is None:

            return

        arrived_stop = (
            prediction[
                "current_stop"
            ]
        )

        arrival_time = (
            prediction[
                "arrival_time"
            ]
        )

        # ==================================================
        # PARA ANIMAÇÃO DO SEGMENTO
        # ==================================================

        self.cancel_bus_animation()

        # ==================================================
        # COLOCA EXATAMENTE NO PONTO
        # ==================================================

        self.place_bus_at_stop(
            arrived_stop
        )

        # ==================================================
        # ATUALIZA MODELO
        # ==================================================

        self.simulation.confirm_arrival(
            arrived_stop=arrived_stop,
            arrival_time=arrival_time,
            delay=prediction[
                "fuzzy_delay_minutes"
            ],
            confidence=prediction[
                "confidence"
            ]
        )

        # ==================================================
        # INFORMA
        # ==================================================

        self.add_prediction_text(

            "\n>>> PONTO CONCRETIZADO <<<\n"

            f"Ponto atual: "
            f"{arrived_stop}\n"

            f"Horário: "
            f"{arrival_time}\n"

            f"Atraso anterior: "
            f"{prediction['fuzzy_delay_minutes']:+.2f} min\n"

            f"Confiança: "
            f"{prediction['confidence']:.2f}\n"
        )

        self.update_state()

        # ==================================================
        # DESTINO
        # ==================================================

        if (
            arrived_stop
            == self.destination_stop
        ):

            self.finish_trip()

            return

        # ==================================================
        # LIMPA PREVISÃO ANTIGA
        # ==================================================

        self.next_prediction = None

        self.active_bus_prediction = None

        # ==================================================
        # NOVO TRECHO
        # ==================================================

        self.set_state(
            SimulationState.RUNNING
        )

        self.add_prediction_text(

            "\n>>> RECALCULANDO A PARTIR DE "
            f"{arrived_stop} <<<\n"
        )

        self.process_next_segment()

    # ======================================================
    # FINALIZA VIAGEM
    # ======================================================

    def finish_trip(self):

        self.trip_running = False

        self.cancel_bus_animation()

        self.active_bus_prediction = None

        self.next_prediction = None

        # Mantém o ônibus no destino por enquanto.
        #
        # Não removemos imediatamente para que
        # visualmente fique claro onde a viagem terminou.

        if self.destination_stop:

            self.place_bus_at_stop(
                self.destination_stop
            )

        self.set_state(
            SimulationState.FINISHED
        )

        self.update_state()

        self.add_prediction_text(

            "\n================================\n"

            ">>> DESTINO ALCANÇADO <<<\n"

            "================================\n"
        )

    # ======================================================
    # ESTADO DO MODELO
    # ======================================================

    def update_state(self):

        state = (
            self.simulation.get_state()
        )

        text = (

            f"Ponto atual: "
            f"{state['current_stop']}\n"

            f"Horário: "
            f"{state['current_time']}\n"

            f"Atraso anterior: "
            f"{state['previous_delay']:+.2f} min\n"

            f"Confiança: "
            f"{state['previous_confidence']:.2f}"
        )

        self.state_label.config(
            text=text
        )

    # ======================================================
    # TEXTO
    # ======================================================

    def add_prediction_text(
        self,
        message
    ):

        self.prediction_text.config(
            state="normal"
        )

        self.prediction_text.insert(
            tk.END,
            message
        )

        self.prediction_text.see(
            tk.END
        )

        self.prediction_text.config(
            state="disabled"
        )


# ==========================================================
# EXECUÇÃO
# ==========================================================

root = tk.Tk()

app = BusSimulationApp(
    root
)


def close_application():

    app.trip_running = False

    app.cancel_bus_animation()

    try:

        app.worker.stop()

    except Exception:
        pass

    root.destroy()


root.protocol(
    "WM_DELETE_WINDOW",
    close_application
)

root.mainloop()