import sys
import os
import copy
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from PIL import Image, ImageTk

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from Agents.agent_network import AgentNetwork
from Data.stop_loader import StopLoader
from Data.route_loader import RouteLoader
from Schedules.schedule_loader import ScheduleLoader
from Services.trip_manager import TripManager

from tkintermapview import TkinterMapView

from Api.routing_api import get_route
from Fuzzy.delay_fuzzy import DelayFuzzySystem



# ==========================================================
# CONFIGURAÇÃO
# ==========================================================

STOPS_FILE = "Data/stops.csv"
ROUTES_FILE = "Data/routes.csv"
SCHEDULE_FILE = "Data/schedules.csv"

UPDATE_INTERVAL_MS = 1000


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

network.connect_routes_from_loader(route_loader)

schedule_loader = ScheduleLoader(SCHEDULE_FILE)
schedule_loader.load()

fuzzy = DelayFuzzySystem()

trip_manager = TripManager(
    network=network,
    route_loader=route_loader,
    schedule_loader=schedule_loader,
    fuzzy=fuzzy
)

# A interface não inicia viagens manualmente.
# O TripManager é o responsável por acompanhar o relógio.
if hasattr(trip_manager, "initialize"):
    trip_manager.initialize(datetime.now())
else:
    trip_manager.load_scheduled_trips(datetime.now())


# ==========================================================
# INTERFACE
# ==========================================================

class BusSimulationApp:

    def __init__(self, root):

        self.root = root
        self.root.title(
            "Monitoramento do Transporte Público"
        )

        self.root.geometry("1200x700")
        self.root.minsize(1050, 620)
        self.bus_icon = ImageTk.PhotoImage(
                    Image.open(
                        os.path.join(os.path.dirname(__file__), "bus_icon.png")
                    ).resize((40, 40), Image.Resampling.LANCZOS)
                )
        
        # --------------------------------------------------
        # CONSULTA
        # --------------------------------------------------

        self.selected_route_id = None
        self.selected_stop_id = None

        # --------------------------------------------------
        # MAPA
        # --------------------------------------------------

        self.route_path = None
        self.stop_markers = []
        self.bus_markers = {}

        # Cache para não chamar OSRM toda hora.
        self.route_cache = {}

        # --------------------------------------------------
        # INTERFACE
        # --------------------------------------------------

        self.create_widgets()
        self.load_routes()

        # Primeira atualização imediata.
        self.refresh_interface()

        

    # ======================================================
    # WIDGETS
    # ======================================================

    def create_widgets(self):

        main_frame = ttk.Frame(self.root)
        main_frame.pack(
            fill="both",
            expand=True
        )

        # --------------------------------------------------
        # PAINEL ESQUERDO
        # Aproximadamente 35% da janela.
        # --------------------------------------------------

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

        left_frame.pack_propagate(False)

        # --------------------------------------------------
        # MAPA
        # --------------------------------------------------

        right_frame = ttk.Frame(main_frame)

        right_frame.pack(
            side="right",
            fill="both",
            expand=True,
            padx=(0, 10),
            pady=10
        )

        # --------------------------------------------------
        # TÍTULO
        # --------------------------------------------------

        ttk.Label(
            left_frame,
            text="MONITORAMENTO DO\nTRANSPORTE PÚBLICO",
            font=("Arial", 17, "bold"),
            justify="center"
        ).pack(pady=(12, 18))

        # --------------------------------------------------
        # CONSULTAR LINHA
        # --------------------------------------------------

        line_frame = ttk.LabelFrame(
            left_frame,
            text="Consultar linha",
            padding=15
        )

        line_frame.pack(
            fill="x"
        )

        ttk.Label(
            line_frame,
            text="Linha:"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=5
        )

        self.route_combo = ttk.Combobox(
            line_frame,
            state="readonly",
            width=25
        )

        self.route_combo.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=5
        )

        self.route_combo.bind(
            "<<ComboboxSelected>>",
            self.route_selected
        )

        line_frame.columnconfigure(
            1,
            weight=1
        )

        # --------------------------------------------------
        # SITUAÇÃO DA LINHA
        # --------------------------------------------------

        situation_frame = ttk.LabelFrame(
            left_frame,
            text="Situação da linha",
            padding=15
        )

        situation_frame.pack(
            fill="x",
            pady=12
        )

        self.situation_text = tk.Text(
            situation_frame,
            height=10,
            state="disabled",
            wrap="word",
            relief="flat",
            background="#f5f5f5"
        )

        self.situation_text.pack(
            fill="both",
            expand=True
        )

        # --------------------------------------------------
        # CONSULTAR CHEGADA
        # --------------------------------------------------

        consultation_frame = ttk.LabelFrame(
            left_frame,
            text="Consultar chegada",
            padding=15
        )

        consultation_frame.pack(
            fill="x"
        )

        ttk.Label(
            consultation_frame,
            text="Ponto:"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=5
        )

        self.stop_combo = ttk.Combobox(
            consultation_frame,
            state="readonly",
            width=25
        )

        self.stop_combo.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=5
        )

        self.consult_button = ttk.Button(
            consultation_frame,
            text="CONSULTAR",
            command=self.consult_arrival
        )

        self.consult_button.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(12, 5)
        )

        self.arrival_label = ttk.Label(
            consultation_frame,
            text="Selecione um ponto para consultar.",
            wraplength=330,
            justify="left"
        )

        self.arrival_label.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(8, 0)
        )

        consultation_frame.columnconfigure(
            1,
            weight=1
        )

        # --------------------------------------------------
        # RODAPÉ
        # --------------------------------------------------

        self.clock_label = ttk.Label(
            left_frame,
            text="",
            font=("Arial", 9)
        )

        self.clock_label.pack(
            side="bottom",
            pady=5
        )

        # --------------------------------------------------
        # MAPA
        # --------------------------------------------------

        self.map_widget = TkinterMapView(
            right_frame,
            corner_radius=0
        )

        self.map_widget.pack(
            fill="both",
            expand=True
        )

        self.map_widget.set_position(
            -22.2231,
            -54.8120
        )

        self.map_widget.set_zoom(14)

    # ======================================================
    # ROTAS
    # ======================================================

    def load_routes(self):

        routes = route_loader.get_route_ids()

        self.route_combo["values"] = routes

        if routes:
            self.route_combo.current(0)
            self.route_selected()

    def route_selected(self, event=None):

        route_id = self.route_combo.get()

        if not route_id:
            return

        self.selected_route_id = route_id

        route = route_loader.get_route(route_id)

        self.load_stop_selector(route)
        self.draw_route(route)
        self.refresh_selected_line()

    def load_stop_selector(self, route):

        if not route:
            self.stop_combo["values"] = []
            return

        stop_ids = [
            stop["stop_id"]
            for stop in route
        ]

        self.stop_combo["values"] = stop_ids

        # Não sobrescreve a escolha do usuário a cada atualização.
        # Isso é importante porque a interface atualiza a linha
        # automaticamente a cada segundo.
        current_selection = self.stop_combo.get()

        if current_selection in stop_ids:
            self.stop_combo.set(current_selection)
        elif stop_ids:
            self.stop_combo.current(0)

    # ======================================================
    # MAPA
    # ======================================================

    def draw_route(self, route):

        self.cancel_map_objects()

        if not route:
            return

        coordinates = []

        for item in route:

            stop = stop_loader.get_stop(
                item["stop_id"]
            )

            if stop is None:
                continue

            latitude = float(stop["latitude"])
            longitude = float(stop["longitude"])

            coordinates.append(
                (latitude, longitude)
            )

            marker = self.map_widget.set_marker(
                latitude,
                longitude,
                text=item["stop_id"],
            )

            self.stop_markers.append(marker)

        if len(coordinates) < 2:
            return

        middle = coordinates[len(coordinates) // 2]

        self.map_widget.set_position(
            middle[0],
            middle[1]
        )

        self.map_widget.set_zoom(14)

        # --------------------------------------------------
        # OSRM
        # --------------------------------------------------

        if self.selected_route_id in self.route_cache:

            osrm_route = self.route_cache[
                self.selected_route_id
            ]

        else:

            try:

                osrm_route = get_route(
                    coordinates
                )

                self.route_cache[
                    self.selected_route_id
                ] = osrm_route

            except Exception as error:

                print(
                    f"Erro ao carregar rota no mapa: {error}"
                )

                osrm_route = {
                    "geometry": coordinates,
                    "legs_geometry": []
                }

        geometry = osrm_route.get(
            "geometry",
            coordinates
        )

        if geometry:

            self.route_path = (
                self.map_widget.set_path(
                    geometry
                )
            )

    def cancel_map_objects(self):

        for marker in self.stop_markers:

            try:
                marker.delete()
            except Exception:
                pass

        self.stop_markers = []

        for marker in self.bus_markers.values():

            try:
                marker.delete()
            except Exception:
                pass

        self.bus_markers = {}

        if self.route_path is not None:

            try:
                self.route_path.delete()
            except Exception:
                pass

            self.route_path = None

    # ======================================================
    # ATUALIZAÇÃO AUTOMÁTICA
    # ======================================================

    def refresh_interface(self):

        now = datetime.now()

        try:
            trip_manager.update(now)
        except Exception as error:

            print(
                f"[TripManager] erro na atualização: {error}"
            )

        

        if self.selected_route_id:

            self.refresh_selected_line()

        self.root.after(
            UPDATE_INTERVAL_MS,
            self.refresh_interface
        )

    # ======================================================
    # SITUAÇÃO DA LINHA
    # ======================================================

    def refresh_selected_line(self):

        if not self.selected_route_id:
            return

        trips = [
            trip
            for trip in trip_manager.get_trips()
            if trip["route_id"] == self.selected_route_id
        ]

        active_trips = [
            trip
            for trip in trips
            if trip["status"] == "active"
        ]

        scheduled_trips = [
            trip
            for trip in trips
            if trip["status"] == "scheduled"
        ]

        # --------------------------------------------------
        # HÁ ÔNIBUS EM OPERAÇÃO
        # --------------------------------------------------

        if active_trips:

            self.update_active_situation(
                active_trips
            )

            self.update_map_buses(
                active_trips
            )

            return

        # --------------------------------------------------
        # NÃO HÁ ÔNIBUS AGORA
        # --------------------------------------------------

        self.clear_bus_markers()

        if scheduled_trips:

            next_trip = min(
                scheduled_trips,
                key=lambda trip: self.parse_time(
                    trip["departure_time"]
                )
            )

            self.update_scheduled_situation(
                next_trip
            )

            return

        # --------------------------------------------------
        # SEM VIAGEM FUTURA
        # --------------------------------------------------

        self.set_situation(
            "LINHA: " + self.selected_route_id + "\n\n"
            "Status: SEM VIAGEM EM OPERAÇÃO\n\n"
            "Não há uma viagem programada "
            "para este horário."
        )

    # ======================================================
    # SITUAÇÃO — ATIVA
    # ======================================================

    def update_active_situation(
        self,
        active_trips
    ):

        lines = [
            f"LINHA: {self.selected_route_id}",
            "",
            "Status: EM OPERAÇÃO",
            ""
        ]

        for index, trip in enumerate(active_trips, start=1):

            state = trip_manager.get_trip_state(
                trip
            )

            simulation = trip["simulation"]

            current_stop = state.get(
                "current_stop"
            )

            prediction = trip.get(
                "next_prediction"
            )

            next_stop = None
            arrival_time = None

            if prediction:

                next_stop = prediction.get(
                    "next_stop"
                )

                arrival_time = prediction.get(
                    "arrival_time"
                )

            departure_time = trip.get(
                "departure_time",
                "--:--:--"
            )

            lines.append(
                f"Ônibus {index} - {departure_time}"
            )

            lines.append(
                f"  Direção: {state.get('direction')}"
            )

            lines.append(
                f"  Atual: {current_stop}"
            )

            if next_stop:

                lines.append(
                    f"  Próximo: {next_stop}"
                )

            if arrival_time:

                lines.append(
                    f"  Chegada estimada: {arrival_time}"
                )

            lines.append(
                f"  Atraso: "
                f"{state.get('previous_delay', 0):.2f} min"
            )

            lines.append(
                f"  Confiança: "
                f"{state.get('previous_confidence', 0):.1f}%"
            )

            if index < len(active_trips):

                lines.append("")

        self.set_situation(
            "\n".join(lines)
        )

        # Mantém o seletor de pontos sincronizado
        # com a primeira viagem ativa.
        first_trip = active_trips[0]

        route = route_loader.get_route(
            first_trip["route_id"]
        )

        self.load_stop_selector(route)

    # ======================================================
    # SITUAÇÃO — PROGRAMADA
    # ======================================================

    def update_scheduled_situation(
        self,
        trip
    ):

        self.set_situation(
            f"LINHA: {self.selected_route_id}\n\n"
            "Status: PROGRAMADA\n\n"
            f"Próxima saída: {trip['departure_time']}\n"
            f"Direção: {trip['direction']}\n\n"
            "O ônibus aparecerá automaticamente "
            "no mapa quando a viagem começar."
        )

    # ======================================================
    # TEXTO DA SITUAÇÃO
    # ======================================================

    def set_situation(self, text):

        self.situation_text.config(
            state="normal"
        )

        self.situation_text.delete(
            "1.0",
            tk.END
        )

        self.situation_text.insert(
            "1.0",
            text
        )

        self.situation_text.config(
            state="disabled"
        )

    # ======================================================
    # ÔNIBUS NO MAPA
    # ======================================================

    def update_map_buses(self, active_trips):

        active_ids = set()

        for index, trip in enumerate(active_trips, start=1):

            trip_id = trip["trip_id"]
            active_ids.add(trip_id)

            position = self.get_visual_bus_position(
                trip
            )

            if position is None:
                continue

            latitude, longitude = position

            direction = trip.get(
                "direction",
                ""
            )

            departure_time = trip.get(
                "departure_time",
                "--:--:--"
            )

            text = (
                f"Ônibus {index}"
                f" - {departure_time}"
            )

            if trip_id in self.bus_markers:

                marker = self.bus_markers[
                    trip_id
                ]

                try:

                    marker.set_position(
                        latitude,
                        longitude
                    )

                    marker.set_text(
                        text
                    )

                except Exception:

                    try:
                        marker.delete()
                    except Exception:
                        pass

                    self.bus_markers[
                        trip_id
                    ] = self.map_widget.set_marker(
                        latitude,
                        longitude,
                        text=text,
                        icon=self.bus_icon,
                        icon_anchor="center"
                    )

            else:

                self.bus_markers[
                    trip_id
                ] = self.map_widget.set_marker(
                    latitude,
                    longitude,
                    text=text,
                    icon=self.bus_icon,
                    icon_anchor="center"
                )

        # Remove marcadores de viagens que
        # deixaram de estar ativas.
        for trip_id in list(
            self.bus_markers.keys()
        ):

            if trip_id not in active_ids:

                try:
                    self.bus_markers[trip_id].delete()
                except Exception:
                    pass

                del self.bus_markers[trip_id]

    def clear_bus_markers(self):

        for marker in self.bus_markers.values():

            try:
                marker.delete()
            except Exception:
                pass

        self.bus_markers = {}

    # ======================================================
    # POSIÇÃO VISUAL DO ÔNIBUS
    # ======================================================

    def get_visual_bus_position(self, trip):

        simulation = trip["simulation"]

        current_stop = simulation.current_stop

        if not current_stop:
            return None

        prediction = trip.get(
            "next_prediction"
        )

        # Se ainda não há previsão do próximo
        # trecho, mostra no ponto atual.
        if not prediction:

            return self.stop_coordinates(
                current_stop
            )

        next_stop = prediction.get(
            "next_stop"
        )

        departure = self.parse_prediction_time(
            prediction.get("departure_time")
        )

        arrival = self.parse_prediction_time(
            prediction.get("arrival_time")
        )

        if (
            not next_stop
            or departure is None
            or arrival is None
            or arrival <= departure
        ):

            return self.stop_coordinates(
                current_stop
            )

        now = datetime.now()

        # O modelo já deveria ter avançado.
        if now >= arrival:

            return self.stop_coordinates(
                next_stop
            )

        # Ainda não saiu.
        if now <= departure:

            return self.stop_coordinates(
                current_stop
            )

        total = (
            arrival - departure
        ).total_seconds()

        elapsed = (
            now - departure
        ).total_seconds()

        progress = elapsed / total

        progress = max(
            0.0,
            min(1.0, progress)
        )

        start = self.stop_coordinates(
            current_stop
        )

        end = self.stop_coordinates(
            next_stop
        )

        if start is None or end is None:
            return start

        latitude = (
            start[0]
            + (
                end[0] - start[0]
            ) * progress
        )

        longitude = (
            start[1]
            + (
                end[1] - start[1]
            ) * progress
        )

        return latitude, longitude

    # ======================================================
    # COORDENADAS
    # ======================================================

    def stop_coordinates(self, stop_id):

        stop = stop_loader.get_stop(
            stop_id
        )

        if stop is None:
            return None

        return (
            float(stop["latitude"]),
            float(stop["longitude"])
        )

    # ======================================================
    # HORÁRIOS
    # ======================================================

    @staticmethod
    def parse_time(value):

        if isinstance(value, datetime):
            return value

        for format_ in (
            "%H:%M:%S",
            "%H:%M"
        ):

            try:

                parsed = datetime.strptime(
                    str(value),
                    format_
                )

                now = datetime.now()

                return parsed.replace(
                    year=now.year,
                    month=now.month,
                    day=now.day
                )

            except ValueError:
                continue

        return None

    def parse_prediction_time(self, value):

        if value is None:
            return None

        return self.parse_time(value)

    # ======================================================
    # CONSULTA DE CHEGADA
    # ======================================================

    def consult_arrival(self):

        if not self.selected_route_id:
            self.arrival_label.config(
                text="Selecione uma linha."
            )
            return

        target_stop = self.stop_combo.get()

        if not target_stop:
            self.arrival_label.config(
                text="Selecione um ponto."
            )
            return

        active_trips = [
            trip
            for trip in trip_manager.get_trips()
            if trip["route_id"] == self.selected_route_id
            and trip["status"] == "active"
        ]

        if not active_trips:
            scheduled = [
                trip
                for trip in trip_manager.get_trips()
                if trip["route_id"] == self.selected_route_id
                and trip["status"] == "scheduled"
            ]

            if scheduled:
                next_trip = min(
                    scheduled,
                    key=lambda trip: self.parse_time(
                        trip["departure_time"]
                    )
                )

                self.arrival_label.config(
                    text=(
                        "Nenhum ônibus está em operação "
                        "nesta linha agora.\n\n"
                        f"Próxima saída: {next_trip['departure_time']}"
                    )
                )
            else:
                self.arrival_label.config(
                    text="Não há ônibus em operação nesta linha."
                )

            return

        results = []

        for trip in active_trips:

            simulation = trip["simulation"]
            current_stop = simulation.current_stop

            if not current_stop:
                continue

            route = route_loader.get_route(
                trip["route_id"]
            )

            if not route:
                continue

            stop_ids = [
                stop["stop_id"]
                for stop in route
            ]

            if target_stop not in stop_ids:
                continue

            current_index = stop_ids.index(current_stop)
            target_index = stop_ids.index(target_stop)

            # O ônibus já passou do ponto consultado.
            if target_index < current_index:
                continue

            # Está exatamente no ponto.
            if target_index == current_index:
                results.append({
                    "trip": trip,
                    "arrival": current_stop,
                    "already_here": True
                })
                continue

            try:
                # A cópia garante que uma consulta nunca altera
                # a viagem real controlada pelo TripManager.
                simulation_copy = copy.deepcopy(
                    simulation
                )

                # IMPORTANTE: NÃO alteramos current_time aqui.
                # Ele já representa o horário lógico do estado atual
                # da viagem e é usado pelo calculate_future().
                result = simulation_copy.calculate_future(
                    destination_stop=target_stop
                )

                arrival = None

                # Formato atual do BusSimulation:
                # {destination_prediction, future_predictions, ...}
                if isinstance(result, dict):
                    destination_prediction = result.get(
                        "destination_prediction"
                    )

                    if destination_prediction:
                        arrival = destination_prediction.get(
                            "arrival_time"
                        )

                    # Compatibilidade caso o destino não venha preenchido.
                    if arrival is None:
                        future = result.get(
                            "future_predictions",
                            []
                        )

                        if future:
                            arrival = future[-1].get(
                                "arrival_time"
                            )

                # Compatibilidade com versões que retornavam
                # diretamente a lista de previsões.
                elif isinstance(result, list) and result:
                    arrival = result[-1].get(
                        "arrival_time"
                    )

                if arrival:
                    results.append({
                        "trip": trip,
                        "arrival": arrival,
                        "already_here": False
                    })

            except Exception as error:
                print(
                    f"[Consulta] erro na viagem "
                    f"{trip['trip_id']}: {error}"
                )

        if not results:
            self.arrival_label.config(
                text=(
                    f"O ponto {target_stop} não está mais à frente "
                    "dos ônibus ativos desta linha, ou não foi "
                    "possível calcular a previsão."
                )
            )
            return

        lines = []

        for index, item in enumerate(results, start=1):

            trip = item["trip"]
            arrival = item["arrival"]
            departure_time = trip.get(
                "departure_time",
                "--:--:--"
            )
            direction = trip.get(
                "direction",
                ""
            )

            if item["already_here"]:
                lines.append(
                    f"Ônibus {index} - {departure_time}: "
                    f"já está em {target_stop}."
                )
            else:
                lines.append(
                    f"Ônibus {index} - {departure_time}: "
                    f"chegada estimada {arrival}"
                )

            if direction:
                lines.append(
                    f"  Direção: {direction}"
                )

        self.arrival_label.config(
            text="\n".join(lines)
        )

    # ======================================================
    # FECHAMENTO
    # ======================================================

    def close_application(self):

        try:
            self.root.destroy()
        except Exception:
            pass


# ==========================================================
# EXECUÇÃO
# ==========================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = BusSimulationApp(root)

    root.protocol(
        "WM_DELETE_WINDOW",
        app.close_application
    )

    root.mainloop()
