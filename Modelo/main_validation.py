from Api.weather_api import get_weather
from Api.traffic_api import get_traffic
from Api.road_api import get_road_type

from Normalization.normalize import ContextNormalizer

from Fuzzy.delay_fuzzy import DelayFuzzySystem
from Fuzzy.inference_analyzer import InferenceAnalyzer

from Validation.validator import FuzzyValidator, print_report


LAT = -22.2231
LON = -54.8120


# ==========================================================
# OBTÉM CONTEXTO
# ==========================================================

context = {}

context.update(
    get_weather(LAT, LON)
)

context.update(
    get_traffic(LAT, LON)
)

context.update(
    get_road_type(LAT, LON)
)

# Variáveis que ainda serão utilizadas posteriormente
context["previous_delay"] = 2
context["previous_confidence"] = 90


# ==========================================================
# NORMALIZAÇÃO
# ==========================================================

normalizer = ContextNormalizer()

normalized = normalizer.normalize(context)

print("Contexto normalizado original:")
print(normalized)


# ==========================================================
# TESTE MANUAL
# ==========================================================

test_context = normalized["normalized"].copy()

# Valores utilizados para testar
# uma condição conhecida da base de regras

test_context["rain"] = 0
test_context["traffic"] = 0
test_context["speed"] = 15
test_context["road_flow"] = 10

print("\nContexto utilizado no fuzzy:")
print(test_context)


# ==========================================================
# MOTOR FUZZY
# ==========================================================

fuzzy = DelayFuzzySystem()

result = fuzzy.compute(test_context)

delay = result["delay"]


# ==========================================================
# REGRAS CARREGADAS
# ==========================================================

print("\n" + "=" * 60)
print("BASE DE CONHECIMENTO")
print("=" * 60)

for rule in fuzzy.knowledge.rules:

    print(
        f'{rule["id"]} '
        f'[{rule["group"]}] '
        f'-> {rule["output"]}'
    )


# ==========================================================
# ANÁLISE DA INFERÊNCIA
# ==========================================================

# Só fazemos a análise detalhada quando
# realmente existem regras ativadas.

if result["activated_rules"]:

    analyzer = InferenceAnalyzer(fuzzy)

    analysis = analyzer.analyze(
        test_context
    )

    print("\n" + "=" * 60)
    print("REGRAS ATIVADAS")
    print("=" * 60)

    for rule in analysis:

        # Mostra apenas regras relevantes
        if rule["activation"] < 0.10:
            continue

        print()

        print(
            f'ID...........: {rule["id"]}'
        )

        print(
            f'Grupo........: {rule["group"]}'
        )

        print(
            f'Ativação.....: '
            f'{rule["activation"]:.3f}'
        )

        print(
            f'Conclusão....: '
            f'{rule["output"]}'
        )

        print("Condições:")

        for cond in rule["conditions"]:

            print(
                f'   {cond["variable"]:8}'
                f' -> {cond["term"]:12}'
                f' μ={cond["membership"]:.3f}'
            )

        print("-" * 60)

else:

    print("\n" + "=" * 60)
    print("REGRAS ATIVADAS")
    print("=" * 60)

    print(
        "Nenhuma regra foi ativada."
     )

    print(
         "O sistema utilizou FALLBACK."
     )


# ==========================================================
# RESULTADO FINAL
# ==========================================================

print("\n" + "=" * 60)
print("RESULTADO FUZZY")
print("=" * 60)

print(
    f"Delay estimado: {result['delay']:.2f}"
)


if result["fallback"]:

    print(
        "Origem: FALLBACK"
    )

else:

    print(
        "Origem: FUZZY"
    )


print("Regras ativadas:")

if result["activated_rules"]:

    for rule in result["activated_rules"]:

        print(
            f'  {rule["id"]} '
            f'-> {rule["output"]} '
            f'(μ={rule["activation"]:.3f})'
        )

else:

    print("  Nenhuma")


# ==========================================================
# FRAMEWORK DE VALIDAÇÃO
# ==========================================================

print("\n")
print("=" * 60)
print("INICIANDO VALIDAÇÃO")
print("=" * 60)

validator = FuzzyValidator(fuzzy)

results = validator.run()

print_report(results)