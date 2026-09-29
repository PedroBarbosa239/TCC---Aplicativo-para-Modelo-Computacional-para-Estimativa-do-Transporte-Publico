"""Simulação controlada de 8 pontos (7 trechos) para o TCC.

Executar na raiz do projeto:
    py simulacao_controlada_8_pontos_alterada.py

Os contextos fuzzy são controlados e baseados em combinações que já
ativaram regras no diagnóstico do projeto. Não são dados de API. A
comparação cinemática mantém os contextos constantes e altera somente
o fator aplicado à velocidade bruta (1.00 ou 0.90).
"""
from __future__ import annotations

import csv
import json
import math
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import matplotlib.pyplot as plt

ROUTE_ID = "101"
BASE_SPEED_FACTOR = 1.00
ADJUSTED_SPEED_FACTOR = 0.90
RAW_CURRENT_SPEED_KMH = 40.0
RAW_FREE_SPEED_KMH = 40.0
OUTPUT_DIR = Path("resultados_simulacao_8_pontos")

STOPS = [
    ("P001", -22.2200, -54.8060),
    ("P002", -22.2255, -54.8145),
    ("P003", -22.2320, -54.8225),
    ("P004", -22.2390, -54.8300),
    ("P005", -22.2450, -54.8380),
    ("P006", -22.2510, -54.8460),
    ("P007", -22.2580, -54.8530),
    ("P008", -22.2650, -54.8600),
]

# Valores escolhidos a partir de contextos documentados como ativadores
# no diagnóstico já realizado. O retorno real de compute() é registrado;
# o script não presume que a ativação ocorrerá sem conferir o resultado.
SCENARIOS = [
    {"id": "C01_A01", "description": "Chuva intensa e tráfego alto", "target_rule": "A01", "target_output": "very_late",
     "context": {"rain": 93.0, "traffic": 75.0, "road_flow": 50.0, "speed": 50.0}},
    {"id": "C02_A02", "description": "Chuva intensa e velocidade baixa", "target_rule": "A02", "target_output": "very_late",
     "context": {"rain": 93.0, "traffic": 50.0, "road_flow": 50.0, "speed": 75.0}},
    {"id": "C03_A03", "description": "Chuva e tráfego moderados", "target_rule": "A03", "target_output": "late",
     "context": {"rain": 60.0, "traffic": 50.0, "road_flow": 50.0, "speed": 50.0}},
    {"id": "C04_A04", "description": "Chuva leve e tráfego baixo", "target_rule": "A04", "target_output": "on_time",
     "context": {"rain": 30.0, "traffic": 25.0, "road_flow": 50.0, "speed": 50.0}},
    {"id": "C05_A05", "description": "Tempo seco, tráfego baixo e velocidade alta", "target_rule": "A05", "target_output": "early",
     "context": {"rain": 5.0, "traffic": 25.0, "road_flow": 50.0, "speed": 25.0}},
    {"id": "C06_A06", "description": "Condições muito favoráveis", "target_rule": "A06", "target_output": "very_early",
     "context": {"rain": 5.0, "traffic": 5.0, "road_flow": 50.0, "speed": 5.0}},
    {"id": "C07_B08", "description": "Tráfego e via muito desfavoráveis", "target_rule": "B08", "target_output": "very_late",
     "context": {"rain": 50.0, "traffic": 95.0, "road_flow": 95.0, "speed": 75.0}},
]


def import_project():
    from Agents.agent_network import AgentNetwork
    from Agents.agent_message import AgentMessage
    from Agents.bus_stop_agent import BusStopAgent
    from Fuzzy.delay_fuzzy import DelayFuzzySystem
    return AgentNetwork, AgentMessage, BusStopAgent, DelayFuzzySystem


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def build_controlled_agent_class(BusStopAgent, factor: float):
    """Aplica o fator no método efetivamente usado pelo BusStopAgent."""
    class ControlledBusStopAgent(BusStopAgent):
        speed_factor = factor

        def estimate_speed(self, current_speed, free_speed):
            base = super().estimate_speed(current_speed, free_speed)
            return base * self.speed_factor

    return ControlledBusStopAgent


def build_network(AgentNetwork, ControlledBusStopAgent, fuzzy):
    network = AgentNetwork()
    if hasattr(network, "set_fuzzy_system"):
        network.set_fuzzy_system(fuzzy)
    else:
        network.fuzzy_system = fuzzy

    agents = {}
    for stop_id, latitude, longitude in STOPS:
        agents[stop_id] = ControlledBusStopAgent(
            stop_id=stop_id, latitude=latitude, longitude=longitude, lines=[ROUTE_ID]
        )
    network.add_agents(list(agents.values()))
    for i in range(len(STOPS) - 1):
        network.connect_agents(STOPS[i][0], STOPS[i + 1][0], route_id=ROUTE_ID)
    return network, agents


def clean_rules(fuzzy_result: dict) -> list[dict]:
    """Usa os graus de ativação retornados pelo próprio DelayFuzzySystem."""
    rules = fuzzy_result.get("activated_rules") or []
    cleaned = []
    for rule in rules:
        cleaned.append({
            "id": str(rule.get("id", rule.get("label", "unknown"))),
            "output": str(rule.get("output", rule.get("consequent", "unknown"))),
            "activation": float(rule.get("activation", 0.0)),
        })
    return cleaned


def run_route(AgentNetwork, AgentMessage, BusStopAgent, DelayFuzzySystem, factor: float) -> list[dict]:
    ControlledAgent = build_controlled_agent_class(BusStopAgent, factor)
    fuzzy = DelayFuzzySystem()
    _network, agents = build_network(AgentNetwork, ControlledAgent, fuzzy)
    message = AgentMessage(
        source_agent=STOPS[0][0], route_id=ROUTE_ID,
        departure_time="05:00:00", arrival_time="05:00:00",
        estimated_delay=50.0, confidence=1.0,
    )
    rows = []

    for i, scenario in enumerate(SCENARIOS):
        origin, destination = STOPS[i], STOPS[i + 1]
        origin_id, destination_id = origin[0], destination[0]
        context = scenario["context"]
        agent = agents[destination_id]
        agent.receive_message(message)

        # O fuzzy recebe somente o contexto normalizado. A cinemática usa
        # os valores RAW e o fator de velocidade controlado.
        full_context = {
            "raw": {
                "current_speed": RAW_CURRENT_SPEED_KMH,
                "free_speed": RAW_FREE_SPEED_KMH,
            },
            "normalized": context,
        }
        # O fuzzy do projeto imprime uma tabela de diagnóstico para cada
        # chamada; capturamos essa saída para manter o console legível.
        with redirect_stdout(StringIO()):
            result = agent.process_trip(message, full_context)

        fuzzy_result = result.get("fuzzy_result") or {}
        activated = clean_rules(fuzzy_result)
        distance = float(result["distance_meters"])
        speed_base = min(RAW_CURRENT_SPEED_KMH, RAW_FREE_SPEED_KMH)
        speed_used = float(result["speed_kmh"])
        travel_seconds = float(result["travel_time_seconds"])
        local_delay = float(fuzzy_result.get("delay", 50.0))
        local_delay_min = float(fuzzy_result.get(
            "delay_minutes", fuzzy.database.delay_to_minutes(local_delay)
        ))
        combined_delay = float(result["estimated_delay"])
        combined_delay_min = float(fuzzy.database.delay_to_minutes(combined_delay))
        confidence = float(result["confidence"])

        if not activated:
            print(f"AVISO: {scenario['id']} não ativou regras no retorno real do fuzzy.")

        print(
            f"{scenario['id']} | {origin_id}->{destination_id} | "
            f"v={speed_used:.2f} km/h | tempo={travel_seconds / 60:.2f} min | "
            f"fuzzy={local_delay:.2f} | combinado={combined_delay:.2f} | "
            f"regras={len(activated)}"
        )
        for rule in activated:
            print(f"    {rule['id']} -> {rule['output']} (μ={rule['activation']:.3f})")

        rows.append({
            "trecho": f"{origin_id} -> {destination_id}",
            "scenario": scenario["id"],
            "description": scenario["description"],
            "target_rule_from_diagnostic": scenario["target_rule"],
            "target_output_from_diagnostic": scenario["target_output"],
            "distancia_m": distance,
            "rain": float(context["rain"]),
            "traffic": float(context["traffic"]),
            "road_flow": float(context["road_flow"]),
            "speed_fuzzy_context": float(context["speed"]),
            "velocidade_api_atual_kmh_controlada": RAW_CURRENT_SPEED_KMH,
            "velocidade_livre_kmh_controlada": RAW_FREE_SPEED_KMH,
            "velocidade_base_kmh": speed_base,
            "fator_velocidade": factor,
            "velocidade_utilizada_kmh": speed_used,
            "tempo_trecho_s": travel_seconds,
            "tempo_trecho_min": travel_seconds / 60.0,
            "atraso_fuzzy_local": local_delay,
            "atraso_fuzzy_local_min": local_delay_min,
            "atraso_herdado": float(message.estimated_delay),
            "atraso_combinado": combined_delay,
            "atraso_combinado_min": combined_delay_min,
            "confianca_combinada": confidence,
            "fallback": bool(fuzzy_result.get("fallback", False)),
            "regras_ativadas": len(activated),
            "ids_regras_ativadas": ";".join(rule["id"] for rule in activated),
            "ativacoes_regras": json.dumps(activated, ensure_ascii=False),
        })

        message = agent.create_message(
            route_id=ROUTE_ID,
            departure_time=result["departure_time"],
            arrival_time=result["arrival_time"],
        )

    return rows


def save_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_comparison(base: list[dict], adjusted: list[dict]) -> None:
    labels = [r["trecho"] for r in base]
    x = list(range(len(labels)))
    for field, ylabel, title, filename in [
        ("velocidade_utilizada_kmh", "Velocidade (km/h)", "Velocidade utilizada por trecho", "velocidade_segmentos.png"),
        ("tempo_trecho_min", "Tempo (min)", "Tempo de deslocamento por trecho", "tempo_segmentos.png"),
    ]:
        plt.figure(figsize=(11, 5))
        plt.plot(x, [r[field] for r in base], marker="o", label="Fator 1,00")
        plt.plot(x, [r[field] for r in adjusted], marker="o", label="Fator 0,90")
        plt.xticks(x, labels, rotation=35, ha="right")
        plt.ylabel(ylabel)
        plt.xlabel("Trecho")
        plt.title(title)
        plt.grid(alpha=0.25)
        plt.legend()
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / filename, dpi=300)
        plt.close()

    plt.figure(figsize=(11, 5))
    plt.plot(x, [r["atraso_fuzzy_local_min"] for r in adjusted], marker="o")
    plt.xticks(x, labels, rotation=35, ha="right")
    plt.ylabel("Saída fuzzy local (min, escala do projeto)")
    plt.xlabel("Trecho")
    plt.title("Saída fuzzy local por trecho (fator 0,90)")
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "atraso_fuzzy.png", dpi=300)
    plt.close()

    plt.figure(figsize=(11, 5))
    plt.bar(x, [r["regras_ativadas"] for r in adjusted])
    plt.xticks(x, labels, rotation=35, ha="right")
    plt.ylabel("Quantidade de regras ativadas")
    plt.xlabel("Trecho")
    plt.title("Regras fuzzy ativadas por trecho (fator 0,90)")
    plt.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "regras_ativadas.png", dpi=300)
    plt.close()


def generate_report(base: list[dict], adjusted: list[dict]) -> None:
    base_total = sum(r["tempo_trecho_min"] for r in base)
    adjusted_total = sum(r["tempo_trecho_min"] for r in adjusted)
    delta = adjusted_total - base_total
    pct = (delta / base_total * 100.0) if base_total else 0.0
    activated_total = sum(r["regras_ativadas"] for r in adjusted)
    lines = [
        "# Simulação controlada da rota com 8 pontos", "",
        "## Objetivo", "",
        "Observar a inferência fuzzy em sete contextos controlados, distribuídos por sete trechos, e comparar o tempo cinemático usando fatores de velocidade 1,00 e 0,90.", "",
        "Os contextos são valores controlados baseados em casos já documentados como ativadores no diagnóstico do projeto. Não representam leituras ao vivo de APIs.", "",
        "## Contextos por trecho", "",
        "| Trecho | Cenário | Contexto (rain, traffic, road_flow, speed) | Regras ativadas | Saída fuzzy | Combinado | Confiança |", "|---|---|---|---|---:|---:|---:|",
    ]
    for r in adjusted:
        ctx = f"{r['rain']:g}, {r['traffic']:g}, {r['road_flow']:g}, {r['speed_fuzzy_context']:g}"
        lines.append(f"| {r['trecho']} | {r['scenario']} | {ctx} | {r['ids_regras_ativadas'] or 'nenhuma'} | {r['atraso_fuzzy_local']:.2f} | {r['atraso_combinado']:.2f} | {r['confianca_combinada']:.3f} |")
    lines += [
        "", "## Comparação cinemática", "",
        "| Métrica | Fator 1,00 | Fator 0,90 |", "|---|---:|---:|",
        f"| Tempo total (min) | {base_total:.3f} | {adjusted_total:.3f} |",
        f"| Diferença (min) | — | {delta:.3f} |",
        f"| Variação percentual | — | {pct:.2f}% |", "",
        "A distância e os contextos fuzzy foram mantidos constantes entre as duas execuções. O fator foi aplicado pelo método `estimate_speed` sobrescrito na subclasse experimental, isto é, no ponto efetivamente usado pelo `BusStopAgent` para calcular o tempo do trecho.", "",
        "## Regras", "",
        f"Total de ativações de regras na execução com fator 0,90: **{activated_total}**. A ativação e o grau μ são extraídos do retorno `activated_rules` do `DelayFuzzySystem`, sem estimativa por análise textual da regra.", "",
        "## Limitações", "",
        "Os contextos são sintéticos/controlados, e a velocidade bruta de 40 km/h é mantida constante para isolar o efeito do fator. Os resultados não devem ser apresentados como desempenho observado em operação real nem como medição de latência de API.", "",
        "## Arquivos", "",
        "- `resultados_segmentos.csv` — comparação lado a lado por trecho.",
        "- `resultado_fator_1_00.csv` e `resultado_fator_0_90.csv` — resultados individuais.",
        "- `resumo_simulacao.json` — dados estruturados completos.",
        "- `velocidade_segmentos.png`, `tempo_segmentos.png`, `atraso_fuzzy.png`, `regras_ativadas.png` — gráficos.",
    ]
    (OUTPUT_DIR / "relatorio_simulacao.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if len(STOPS) != len(SCENARIOS) + 1:
        raise ValueError("A simulação exige um cenário por trecho (8 pontos = 7 cenários).")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    AgentNetwork, AgentMessage, BusStopAgent, DelayFuzzySystem = import_project()

    print("SIMULAÇÃO CONTROLADA — 8 PONTOS / 7 TRECHOS")
    print("Contextos predefinidos; não são dados de API.\n")
    base = run_route(AgentNetwork, AgentMessage, BusStopAgent, DelayFuzzySystem, BASE_SPEED_FACTOR)
    print("\n--- Reexecução com fator de velocidade 0,90 ---")
    adjusted = run_route(AgentNetwork, AgentMessage, BusStopAgent, DelayFuzzySystem, ADJUSTED_SPEED_FACTOR)

    save_csv(OUTPUT_DIR / "resultado_fator_1_00.csv", base)
    save_csv(OUTPUT_DIR / "resultado_fator_0_90.csv", adjusted)
    comparison = []
    for b, a in zip(base, adjusted):
        comparison.append({
            "trecho": b["trecho"], "scenario": b["scenario"], "distancia_m": b["distancia_m"],
            "velocidade_fator_1_00_kmh": b["velocidade_utilizada_kmh"],
            "velocidade_fator_0_90_kmh": a["velocidade_utilizada_kmh"],
            "tempo_fator_1_00_min": b["tempo_trecho_min"],
            "tempo_fator_0_90_min": a["tempo_trecho_min"],
            "diferenca_tempo_min": a["tempo_trecho_min"] - b["tempo_trecho_min"],
            "atraso_fuzzy_local": a["atraso_fuzzy_local"],
            "atraso_combinado": a["atraso_combinado"],
            "confianca_combinada": a["confianca_combinada"],
            "regras_ativadas": a["regras_ativadas"],
            "ids_regras_ativadas": a["ids_regras_ativadas"],
            "ativacoes_regras": a["ativacoes_regras"],
        })
    save_csv(OUTPUT_DIR / "resultados_segmentos.csv", comparison)
    plot_comparison(base, adjusted)
    generate_report(base, adjusted)

    summary = {
        "route_id": ROUTE_ID,
        "stops": [s[0] for s in STOPS],
        "scenarios": SCENARIOS,
        "factor_1_00": base,
        "factor_0_90": adjusted,
        "total_time_factor_1_00_min": sum(r["tempo_trecho_min"] for r in base),
        "total_time_factor_0_90_min": sum(r["tempo_trecho_min"] for r in adjusted),
    }
    (OUTPUT_DIR / "resumo_simulacao.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\nResumo")
    print(f"Trechos: {len(adjusted)}")
    print(f"Ativações fuzzy (fator 0,90): {sum(r['regras_ativadas'] for r in adjusted)}")
    print(f"Tempo total (fator 1,00): {summary['total_time_factor_1_00_min']:.3f} min")
    print(f"Tempo total (fator 0,90): {summary['total_time_factor_0_90_min']:.3f} min")
    print(f"Aumento: {summary['total_time_factor_0_90_min'] - summary['total_time_factor_1_00_min']:.3f} min")
    print(f"Arquivos: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
