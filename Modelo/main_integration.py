from Agents.agent_network import AgentNetwork

from Data.stop_loader import StopLoader
from Data.route_loader import RouteLoader
from Schedules.schedule_loader import ScheduleLoader

from Simulation.bus_simulation import BusSimulation

from datetime import datetime, timedelta


# ==========================================================
# CONFIGURAÇÃO
# ==========================================================

STOPS_FILE = "Data/stops.csv"
ROUTES_FILE = "Data/routes.csv"
SCHEDULE_FILE = "Data/schedules.csv"

ROUTE_ID = "101"

ORIGIN_STOP = "P001"

DESTINATION_STOP = "P003"


# ==========================================================
# CARREGAMENTO DOS PONTOS
# ==========================================================

stop_loader = StopLoader(
    STOPS_FILE
)

stop_loader.load()

agents = stop_loader.create_agents()


# ==========================================================
# CRIA REDE DE AGENTES
# ==========================================================

network = AgentNetwork()

network.add_agents(
    agents
)


# ==========================================================
# CARREGAMENTO DAS ROTAS
# ==========================================================

route_loader = RouteLoader(
    ROUTES_FILE
)

route_loader.load()


# ==========================================================
# CONECTA OS AGENTES DE ACORDO COM AS ROTAS
# ==========================================================

network.connect_routes_from_loader(
    route_loader
)


# ==========================================================
# CARREGAMENTO DOS HORÁRIOS
# ==========================================================

schedule_loader = ScheduleLoader(
    SCHEDULE_FILE
)

schedule_loader.load()


# ==========================================================
# CRIA SIMULAÇÃO
# ==========================================================

simulation = BusSimulation(
    network=network,
    route_loader=route_loader,
    schedule_loader=schedule_loader
)


# ==========================================================
# HORÁRIO DE TESTE
# ==========================================================
#
# Para o teste, usamos 10 segundos à frente do horário atual.
#
# Em uma etapa posterior, vamos substituir isso pelo
# horário vindo do ScheduleLoader / CSV.
#

departure_time = (
    datetime.now()
    + timedelta(seconds=10)
).strftime("%H:%M:%S")


# ==========================================================
# EXECUTA SIMULAÇÃO EM TEMPO REAL
# ==========================================================

result = simulation.run_realtime(
    route_id=ROUTE_ID,
    origin_stop=ORIGIN_STOP,
    destination_stop=DESTINATION_STOP,
    departure_time=departure_time
)


# ==========================================================
# RESULTADO FINAL
# ==========================================================

print("\n========================================")
print("          RESULTADO FINAL")
print("========================================")

print(result)