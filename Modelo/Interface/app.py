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

network.connect_routes_from_loader(route_loader)

schedule_loader = ScheduleLoader(SCHEDULE_FILE)
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

        self.root.geometry("700x650")

        # Modelo utilizado pela interface
        self.simulation = simulation

        # Estado da interface
        self.trip_running = False
        self.next_prediction = None
        self.destination_stop = None

        self.create_widgets()

        self.load_routes()


    # ======================================================
    # WIDGETS
    # ======================================================

    def create_widgets(self):

        # --------------------------------------------------
        # TÍTULO
        # --------------------------------------------------

        title = ttk.Label(
            self.root,
            text="MODELO DE ESTIMATIVA DE TRANSPORTE PÚBLICO",
            font=("Arial", 16, "bold")
        )

        title.pack(
            pady=20
        )


        # --------------------------------------------------
        # CONFIGURAÇÃO
        # --------------------------------------------------

        config_frame = ttk.LabelFrame(
            self.root,
            text="Configuração da viagem",
            padding=15
        )

        config_frame.pack(
            fill="x",
            padx=20
        )


        # --------------------------------------------------
        # ROTA
        # --------------------------------------------------

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


        # --------------------------------------------------
        # ORIGEM
        # --------------------------------------------------

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


        # --------------------------------------------------
        # DESTINO
        # --------------------------------------------------

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


        # --------------------------------------------------
        # HORÁRIO
        # --------------------------------------------------

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


        # --------------------------------------------------
        # BOTÃO
        # --------------------------------------------------

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
            self.root,
            text="Estado atual",
            padding=15
        )

        state_frame.pack(
            fill="x",
            padx=20,
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
            self.root,
            text="Previsão",
            padding=15
        )

        prediction_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=5
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


    # ======================================================
    # INICIA VIAGEM
    # ======================================================

    def start_trip(self):

        # ----------------------------------------------
        # PEGA OS VALORES DOS COMBOBOXES
        # ----------------------------------------------

        route_id = self.route_combo.get()
        origin = self.origin_combo.get()
        destination = self.destination_combo.get()
        departure_time = self.time_entry.get().strip()


        # ----------------------------------------------
        # VALIDAÇÃO
        # ----------------------------------------------

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


        # ----------------------------------------------
        # INICIA O MODELO
        # ----------------------------------------------

        try:

            self.simulation.start_trip(
                  route_id=route_id,
    origin_stop=origin,
    departure_time=departure_time
            )

        except Exception as e:

            messagebox.showerror(
                "Erro ao iniciar viagem",
                str(e)
            )

            return


        # ----------------------------------------------
        # ESTADO DA INTERFACE
        # ----------------------------------------------

        self.trip_running = True
        self.next_prediction = None
        self.destination_stop = destination


        # ----------------------------------------------
        # LIMPA A ÁREA DE PREVISÃO
        # ----------------------------------------------

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


        # ----------------------------------------------
        # ATUALIZA ESTADO
        # ----------------------------------------------

        self.update_state()


        # ----------------------------------------------
        # COMEÇA A CALCULAR O PRÓXIMO SEGMENTO
        # ----------------------------------------------

        self.process_next_segment()


    # ======================================================
    # PROCESSA PRÓXIMO SEGMENTO
    # ======================================================

    def process_next_segment(self):

        if not self.trip_running:
            return


        state = self.simulation.get_state()

        current_stop = state["current_stop"]


        # ----------------------------------------------
        # VERIFICA SE CHEGOU AO DESTINO
        # ----------------------------------------------

        if current_stop == self.destination_stop:

            self.finish_trip()

            return


        # ----------------------------------------------
        # CALCULA PREVISÕES A PARTIR DO PONTO ATUAL
        # ----------------------------------------------

        try:

            predictions = self.simulation.calculate_future(
                self.destination_stop
            )

        except Exception as e:

            self.trip_running = False

            messagebox.showerror(
                "Erro na previsão",
                str(e)
            )

            return


        if not predictions:

            self.trip_running = False

            self.add_prediction_text(
                "\nNenhuma previsão disponível.\n"
            )

            return


        # ----------------------------------------------
        # PRIMEIRO PONTO FUTURO
        # ----------------------------------------------

        self.next_prediction = predictions[0]


        next_stop = self.next_prediction["current_stop"]
        arrival_time = self.next_prediction["arrival_time"]


        # ----------------------------------------------
        # MOSTRA A PREVISÃO
        # ----------------------------------------------

        self.add_prediction_text(
            "\n--------------------------------\n"
            f"REFERÊNCIA ATUAL: {current_stop}\n"
            f"PRÓXIMO PONTO: {next_stop}\n"
            f"PREVISÃO DE CHEGADA: {arrival_time}\n"
            f"Atraso fuzzy: "
            f"{self.next_prediction['fuzzy_delay']:.2f}\n"
            f"Atraso temporal: "
            f"{self.next_prediction['fuzzy_delay_minutes']:+.2f} min\n"
        )


        self.update_state()


        # ----------------------------------------------
        # COMEÇA A ESPERAR SEM CONGELAR A INTERFACE
        # ----------------------------------------------

        self.check_arrival()


    # ======================================================
    # VERIFICA SE CHEGOU AO PRÓXIMO PONTO
    # ======================================================

    def check_arrival(self):

        if not self.trip_running:
            return

        if self.next_prediction is None:
            return


        arrival_time = self.next_prediction["arrival_time"]


        try:

            target_time = datetime.strptime(
                arrival_time,
                "%H:%M:%S"
            )

        except ValueError:

            self.trip_running = False

            self.add_prediction_text(
                "\nErro ao interpretar o horário previsto.\n"
            )

            return


        # ----------------------------------------------
        # HORA ATUAL DO COMPUTADOR
        # ----------------------------------------------

        now = datetime.now()


        target_time = target_time.replace(
            year=now.year,
            month=now.month,
            day=now.day
        )


        # ----------------------------------------------
        # AINDA NÃO CHEGOU
        # ----------------------------------------------

        if now < target_time:

            self.root.after(
                500,
                self.check_arrival
            )

            return


        # ----------------------------------------------
        # CHEGOU
        # ----------------------------------------------

        self.concretize_arrival()


    # ======================================================
    # CONCRETIZA A CHEGADA
    # ======================================================

    def concretize_arrival(self):

        prediction = self.next_prediction


        arrived_stop = prediction["current_stop"]
        arrival_time = prediction["arrival_time"]


        # ----------------------------------------------
        # ATUALIZA O MODELO
        # ----------------------------------------------

        self.simulation.current_stop = arrived_stop
        self.simulation.current_time = arrival_time

        self.simulation.previous_delay = (
            prediction["fuzzy_delay_minutes"]
        )

        self.simulation.previous_confidence = (
            prediction["confidence"]
        )


        # ----------------------------------------------
        # MOSTRA QUE O PONTO FOI CONCRETIZADO
        # ----------------------------------------------

        self.add_prediction_text(
    "\n>>> PONTO CONCRETIZADO <<<\n"
    f"Ponto atual: {arrived_stop}\n"
    f"Horário: {arrival_time}\n"
    f"Atraso anterior: "
    f"{prediction['fuzzy_delay_minutes']:+.2f} min\n"
    f"Confiança: "
    f"{prediction['confidence']:.2f}\n"
)


        self.update_state()


        # ----------------------------------------------
        # VERIFICA DESTINO
        # ----------------------------------------------

        if arrived_stop == self.destination_stop:

            self.finish_trip()

            return


        # ----------------------------------------------
        # LIMPA A PREVISÃO ANTERIOR
        # ----------------------------------------------

        self.next_prediction = None


        # ----------------------------------------------
        # NOVO PONTO = NOVA REFERÊNCIA
        # ----------------------------------------------

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
        self.next_prediction = None

        self.update_state()

        self.add_prediction_text(
            "\n================================\n"
            ">>> DESTINO ALCANÇADO <<<\n"
            "================================\n"
        )


    # ======================================================
    # ATUALIZA ESTADO
    # ======================================================

    def update_state(self):

        state = self.simulation.get_state()

        text = (
            f"Ponto atual: {state['current_stop']}\n"
            f"Horário: {state['current_time']}\n"
            f"Atraso anterior: "
            f"{state['previous_delay']:+.2f} min\n"
            f"Confiança: "
            f"{state['previous_confidence']:.2f}"
        )

        self.state_label.config(
            text=text
        )


    # ======================================================
    # ESCREVE NA ÁREA DE PREVISÃO
    # ======================================================

    def add_prediction_text(self, message):

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

root.mainloop()