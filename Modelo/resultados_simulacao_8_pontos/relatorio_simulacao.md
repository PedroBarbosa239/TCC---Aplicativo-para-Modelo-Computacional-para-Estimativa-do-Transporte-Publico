# Simulação controlada da rota com 8 pontos

## Objetivo

Observar a inferência fuzzy em sete contextos controlados, distribuídos por sete trechos, e comparar o tempo cinemático usando fatores de velocidade 1,00 e 0,90.

Os contextos são valores controlados baseados em casos já documentados como ativadores no diagnóstico do projeto. Não representam leituras ao vivo de APIs.

## Contextos por trecho

| Trecho | Cenário | Contexto (rain, traffic, road_flow, speed) | Regras ativadas | Saída fuzzy | Combinado | Confiança |
|---|---|---|---|---:|---:|---:|
| P001 -> P002 | C01_A01 | 93, 75, 50, 50 | A01;F05 | 83.54 | 73.47 | 1.000 |
| P002 -> P003 | C02_A02 | 93, 50, 50, 75 | A02;F04 | 83.54 | 80.52 | 1.000 |
| P003 -> P004 | C03_A03 | 60, 50, 50, 50 | A03;B03;E01;H03 | 62.50 | 67.91 | 1.000 |
| P004 -> P005 | C04_A04 | 30, 25, 50, 50 | A04 | 50.00 | 55.37 | 1.000 |
| P005 -> P006 | C05_A05 | 5, 25, 50, 25 | A05 | 25.00 | 34.11 | 1.000 |
| P006 -> P007 | C06_A06 | 5, 5, 50, 5 | A06 | 7.78 | 15.68 | 1.000 |
| P007 -> P008 | C07_B08 | 50, 95, 95, 75 | B01;B08 | 92.22 | 69.26 | 1.000 |

## Comparação cinemática

| Métrica | Fator 1,00 | Fator 0,90 |
|---|---:|---:|
| Tempo total (min) | 11.833 | 13.083 |
| Diferença (min) | — | 1.250 |
| Variação percentual | — | 10.56% |

A distância e os contextos fuzzy foram mantidos constantes entre as duas execuções. O fator foi aplicado pelo método `estimate_speed` sobrescrito na subclasse experimental, isto é, no ponto efetivamente usado pelo `BusStopAgent` para calcular o tempo do trecho.

## Regras

Total de ativações de regras na execução com fator 0,90: **13**. A ativação e o grau μ são extraídos do retorno `activated_rules` do `DelayFuzzySystem`, sem estimativa por análise textual da regra.

## Limitações

Os contextos são sintéticos/controlados, e a velocidade bruta de 40 km/h é mantida constante para isolar o efeito do fator. Os resultados não devem ser apresentados como desempenho observado em operação real nem como medição de latência de API.

## Arquivos

- `resultados_segmentos.csv` — comparação lado a lado por trecho.
- `resultado_fator_1_00.csv` e `resultado_fator_0_90.csv` — resultados individuais.
- `resumo_simulacao.json` — dados estruturados completos.
- `velocidade_segmentos.png`, `tempo_segmentos.png`, `atraso_fuzzy.png`, `regras_ativadas.png` — gráficos.