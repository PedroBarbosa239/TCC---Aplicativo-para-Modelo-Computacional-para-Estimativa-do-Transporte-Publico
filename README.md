# Sistema de Estimativa de Transporte Público

## 1. Visão geral

Este projeto é o desenvolvimento de um **modelo computacional para
estimativa do transporte público**, com foco na estimativa do
comportamento e do atraso de veículos de transporte coletivo mesmo em
cenários nos quais não exista uma posição GPS continuamente disponível.

O projeto é desenvolvido como parte do **Trabalho de Conclusão de Curso
(TCC)** e busca combinar técnicas de:

-   Lógica Fuzzy;
-   Modelagem baseada em agentes inteligentes;
-   Integração com APIs externas;
-   Normalização e tratamento de dados;
-   Análise e validação de regras;
-   Futuramente, aprendizado de máquina.

A proposta não é simplesmente prever uma posição, mas construir um
modelo capaz de trabalhar com **incerteza, informações incompletas e
diferentes condições do ambiente**, produzindo uma estimativa de
atraso/comportamento do transporte.

------------------------------------------------------------------------

## 2. Objetivo

O objetivo principal é desenvolver um modelo capaz de estimar o atraso
de um veículo de transporte público utilizando informações indiretas do
ambiente e do próprio percurso.

Entre as informações consideradas estão:

-   condições climáticas;
-   intensidade do trânsito;
-   velocidade do veículo;
-   características da via;
-   atraso observado anteriormente;
-   confiança associada à informação anterior;
-   informações relacionadas ao percurso e aos pontos de referência.

A arquitetura foi pensada para permitir que o sistema evolua
progressivamente, começando com um modelo baseado em regras e
posteriormente incorporando agentes inteligentes e aprendizado de
máquina.

------------------------------------------------------------------------

## 3. Problema abordado

Sistemas tradicionais de localização de transporte público normalmente
dependem de GPS ou de outras fontes de posicionamento em tempo real.

Entretanto, podem existir situações nas quais:

-   o GPS não esteja disponível;
-   exista perda ou atraso de comunicação;
-   a posição recebida esteja desatualizada;
-   existam poucos dados históricos;
-   as condições do ambiente alterem significativamente o tempo de
    deslocamento.

Nesse cenário, o projeto busca utilizar **evidências indiretas** para
estimar o comportamento do transporte.

Por exemplo, uma combinação de:

> chuva intensa + trânsito elevado + baixa velocidade + via desfavorável

pode indicar uma alta probabilidade de atraso.

A lógica fuzzy é utilizada justamente para representar esse tipo de
conhecimento de maneira gradual, evitando uma decisão puramente binária.

------------------------------------------------------------------------

# 4. Arquitetura conceitual

A evolução planejada do projeto está organizada em módulos.

``` text
                 ┌──────────────────────┐
                 │     Dados externos   │
                 │ APIs / contexto      │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ Normalização /       │
                 │ preparação dos dados │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │     Lógica Fuzzy     │
                 │                      │
                 │ Regras + conhecimento│
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ Estimativa de atraso │
                 │ / estado do veículo  │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ Agentes inteligentes │
                 │   (próximo módulo)   │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ Machine Learning     │
                 │   (fase futura)      │
                 └──────────────────────┘
```

A arquitetura foi construída de forma incremental para que cada módulo
possa ser validado antes da introdução do próximo.

------------------------------------------------------------------------

# 5. Tecnologias

## Linguagem

-   Python

## Principais bibliotecas

-   `scikit-fuzzy`
-   `NumPy`
-   `scikit-learn` --- planejada para a etapa de Machine Learning
-   `pandas` --- utilizada para manipulação de dados
-   `matplotlib` --- apoio à análise e visualização

## APIs e fontes de dados

Durante o desenvolvimento foram consideradas/integradas fontes externas
para obtenção de contexto ambiental e viário, incluindo:

-   API meteorológica;
-   API de trânsito;
-   Google Maps/serviços de mapas;
-   informações de percurso e vias.

As APIs são utilizadas como fontes de contexto e não como substitutas do
modelo computacional.

------------------------------------------------------------------------

# 6. Normalização dos dados

Os dados obtidos de diferentes fontes possuem escalas e representações
distintas.

Por isso, foi desenvolvido um processo de normalização para transformar
essas informações em valores adequados ao sistema fuzzy.

Entre as informações tratadas estão:

-   chuva;
-   visibilidade;
-   velocidade do vento;
-   velocidade atual;
-   velocidade livre;
-   congestionamento;
-   tipo de via;
-   atraso anterior;
-   confiança da estimativa anterior.

Exemplo de representação:

``` text
Dado bruto
    ↓
Tratamento
    ↓
Normalização
    ↓
Variável fuzzy
    ↓
Inferência
```

O tipo de via também é convertido para uma representação numérica
compatível com o modelo.

------------------------------------------------------------------------

# 7. Sistema de Lógica Fuzzy

A lógica fuzzy constitui o primeiro núcleo de inteligência do sistema.

As principais variáveis utilizadas atualmente são:

-   `Rain`
-   `Traffic`
-   `Road`
-   `Speed`
-   `Delay`

Existe também a variável relacionada ao atraso anterior no contexto
geral do modelo.

O objetivo é transformar valores numéricos contínuos em graus de
pertinência e, posteriormente, utilizar regras linguísticas para estimar
o atraso.

------------------------------------------------------------------------

## 7.1 Variáveis linguísticas

As variáveis possuem termos linguísticos.

### Chuva

Exemplos:

``` text
none
light
moderate
heavy
```

### Trânsito

``` text
very_low
low
medium
high
very_high
```

### Velocidade

``` text
very_slow
slow
normal
fast
very_fast
```

### Via

``` text
very_poor
poor
average
good
excellent
```

### Saída: atraso

``` text
very_early
early
on_time
late
very_late
```

Esses termos representam faixas de comportamento e não valores binários.

------------------------------------------------------------------------

# 8. Base de regras

As regras são armazenadas em arquivo CSV, permitindo separar o
conhecimento do código da aplicação.

Estrutura:

``` text
ID,Grupo,Rain,Traffic,Road,Speed,Delay,Justificativa,Implementada
```

Exemplo:

``` text
A01,A,heavy,high,,,very_late,,TRUE
```

Essa regra representa uma situação na qual:

``` text
Rain = heavy
Traffic = high
→ Delay = very_late
```

Outro exemplo:

``` text
B05,B,,very_low,excellent,very_fast,very_early,,TRUE
```

Representa:

``` text
Traffic = very_low
Road = excellent
Speed = very_fast
→ Delay = very_early
```

O formato permite que novas regras sejam adicionadas sem modificar
diretamente o código Python.

------------------------------------------------------------------------

# 9. Organização dos grupos de regras

A base atual foi organizada em grupos identificados por letras:

``` text
A
B
C
D
E
F
G
H
I
J
```

Esses grupos representam diferentes combinações de conhecimento
utilizadas na construção progressiva da base.

A base atual contém regras como:

-   regras baseadas principalmente em clima;
-   regras baseadas em trânsito;
-   regras combinando trânsito, via e velocidade;
-   regras combinando clima e condições viárias;
-   situações de atraso;
-   situações de normalidade;
-   situações de adiantamento.

A intenção é que essa organização facilite a análise, manutenção e
evolução da base de conhecimento.

------------------------------------------------------------------------

# 10. KnowledgeBase

A classe `KnowledgeBase` é responsável por carregar e construir as
regras fuzzy.

Fluxo:

``` text
rules.csv
   ↓
RuleLoader
   ↓
KnowledgeBase
   ↓
interpretação das condições
   ↓
ctrl.Rule
   ↓
ControlSystem
```

A classe também mantém uma representação das regras contendo:

-   ID;
-   grupo;
-   condições;
-   consequente;
-   objeto da regra fuzzy.

------------------------------------------------------------------------

# 11. Construção automática das regras

As regras são construídas a partir do CSV.

O sistema verifica a coluna:

``` text
Implementada
```

Somente regras marcadas como:

``` text
TRUE
```

são carregadas para o sistema.

As condições preenchidas são combinadas com operador lógico `AND`.

Exemplo:

``` text
Rain = heavy
Traffic = high
Road = poor
Speed = slow
```

é convertido conceitualmente para:

``` text
Rain[heavy]
AND
Traffic[high]
AND
Road[poor]
AND
Speed[slow]
```

e associado a uma saída:

``` text
Delay[very_late]
```

------------------------------------------------------------------------

# 12. Validação da base de regras

Foi desenvolvido um módulo específico para verificar a consistência
lógica da base antes de sua expansão.

A análise atual verifica três situações principais.

## 12.1 Conflitos exatos

O sistema procura regras que possuam exatamente as mesmas condições, mas
produzam saídas diferentes.

Exemplo:

``` text
Regra A:
Traffic = high
Speed = slow
→ late

Regra B:
Traffic = high
Speed = slow
→ very_late
```

Esse caso representa um conflito lógico explícito.

------------------------------------------------------------------------

## 12.2 Regras duplicadas

São identificadas regras que possuem:

-   mesmas condições;
-   mesmo consequente.

Exemplo:

``` text
A01
Traffic = low
Speed = fast
→ early
```

e

``` text
B04
Traffic = low
Speed = fast
→ early
```

Nesse caso, não existe conflito de saída, mas existe redundância.

------------------------------------------------------------------------

## 12.3 Sobreposição entre regras

Também são verificadas relações entre regras gerais e específicas.

Exemplo:

``` text
Regra geral:
Traffic = high
→ late
```

e:

``` text
Regra específica:
Traffic = high
Speed = slow
Road = poor
→ very_late
```

A segunda regra é mais específica e está contida na primeira.

Esse tipo de análise é importante porque permite identificar possíveis
ambiguidades ou interações entre regras.

------------------------------------------------------------------------

# 13. Diagnóstico da validação

A validação gera o arquivo:

``` text
diagnostico_validacao.txt
```

O diagnóstico reúne:

-   análise da base de regras;
-   testes executados;
-   contexto utilizado;
-   regras ativadas;
-   grau de ativação;
-   resultado fuzzy;
-   classificação final;
-   fallback;
-   cobertura das regras.

Exemplo conceitual:

``` text
TESTE X
------------------------------------------------------
Esperado  : late
Obtido    : late
Delay     : 63.42
Origem    : FUZZY

Regras ativadas:

A03 -> late
    μ = 0.72

B06 -> late
    μ = 0.51

STATUS: PASS
```

Isso permite observar não apenas o resultado final, mas também **por que
o sistema chegou àquele resultado**.

------------------------------------------------------------------------

# 14. InferenceAnalyzer

O `InferenceAnalyzer` é utilizado para analisar as regras ativadas
durante a inferência.

Para cada contexto de teste, o sistema pode verificar:

-   quais regras foram ativadas;
-   grau de ativação;
-   condições responsáveis pela ativação;
-   consequente produzido.

Isso é particularmente importante para a análise acadêmica porque
permite transformar a inferência fuzzy em um processo observável e
auditável.

------------------------------------------------------------------------

# 15. Fallback

Quando nenhuma regra fuzzy é significativamente ativada, o sistema
possui um mecanismo de fallback.

Atualmente:

``` text
Nenhuma regra ativada
        ↓
Fallback
        ↓
Delay = 50.0
```

O resultado também informa:

``` text
fallback = True
```

Isso permite diferenciar:

``` text
resultado produzido pelo modelo fuzzy
```

de:

``` text
resultado produzido pelo mecanismo de segurança
```

A taxa de fallback também pode ser utilizada como indicador da cobertura
da base de regras.

------------------------------------------------------------------------

# 16. Testes automáticos

Foi desenvolvido um `TestGenerator` para gerar automaticamente contextos
de teste a partir das regras existentes.

Fluxo:

``` text
Base de regras
      ↓
TestGenerator
      ↓
Contextos de teste
      ↓
DelayFuzzySystem
      ↓
InferenceAnalyzer
      ↓
Classificação
      ↓
Relatório
```

A ideia é verificar se as regras existentes realmente produzem os
comportamentos esperados.

------------------------------------------------------------------------

# 17. Classificação do atraso

O resultado numérico fuzzy é posteriormente convertido em uma classe
linguística através do `DelayClassifier`.

A classificação utiliza as categorias:

``` text
very_early
early
on_time
late
very_late
```

Assim, o modelo pode trabalhar internamente com uma saída numérica
contínua e externamente apresentar uma interpretação linguística.

------------------------------------------------------------------------

# 18. Cobertura das regras

O `CoverageAnalyzer` acompanha quais regras foram utilizadas durante os
testes.

Isso permite identificar:

-   regras nunca ativadas;
-   regras frequentemente ativadas;
-   regiões do espaço de entrada sem cobertura;
-   possíveis lacunas na base de conhecimento.

A cobertura efetiva também é comparada com os casos em que o sistema
precisou utilizar fallback.

------------------------------------------------------------------------

# 19. Consistência da base

O `ConsistencyAnalyzer` é responsável pela análise de consistência
durante a validação.

A combinação entre:

``` text
KnowledgeBase
+
CoverageAnalyzer
+
ConsistencyAnalyzer
+
InferenceAnalyzer
+
TestGenerator
```

forma o atual módulo de verificação da lógica fuzzy.

------------------------------------------------------------------------

# 20. Metodologia de aprimoramento das regras

A evolução da base de conhecimento segue uma abordagem incremental.

### Etapa 1 --- Construção

Criar regras baseadas no conhecimento do domínio.

### Etapa 2 --- Verificação

Executar:

-   conflitos;
-   duplicidades;
-   sobreposições.

### Etapa 3 --- Testes

Gerar contextos e verificar as inferências.

### Etapa 4 --- Cobertura

Identificar regiões pouco ou não representadas.

### Etapa 5 --- Refinamento

Corrigir:

-   regras conflitantes;
-   regras redundantes;
-   regras excessivamente gerais;
-   regras com consequentes inadequados.

### Etapa 6 --- Expansão

Adicionar novas regras somente após compreender as lacunas existentes.

Esse processo evita simplesmente aumentar o número de regras sem
controle da qualidade da base.

------------------------------------------------------------------------

# 21. Agentes inteligentes

O próximo módulo planejado é a introdução de **agentes inteligentes**.

A ideia é representar elementos do sistema de transporte como agentes
capazes de manter informações sobre seu próprio estado e interagir com
outros agentes.

Um possível modelo conceitual é:

``` text
                AGENTE DO ÔNIBUS
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
     Estado         Contexto       Histórico
        │              │              │
        └──────────────┼──────────────┘
                       ▼
                 Inferência Fuzzy
                       │
                       ▼
                Estado estimado
```

Os pontos de parada também podem atuar como elementos inteligentes do
modelo, fornecendo informações para a estimativa do estado do veículo.

------------------------------------------------------------------------

# 22. Interação entre agentes

Uma possibilidade futura é utilizar a informação produzida por um agente
como entrada para o próximo.

Por exemplo:

``` text
Ponto A
  ↓
estimativa + confiança
  ↓
Ponto B
  ↓
nova estimativa
  ↓
Ponto C
```

Dessa forma, o modelo passa a representar uma cadeia de estimativas.

A informação de:

``` text
previous_delay
previous_confidence
```

pode ser utilizada para representar a influência da estimativa anterior
sobre a próxima.

------------------------------------------------------------------------

# 23. Machine Learning

A utilização de Machine Learning é planejada como uma etapa posterior.

Atualmente existe uma limitação importante:

> modelos de aprendizado de máquina precisam de dados históricos
> suficientes para identificar padrões confiáveis.

Portanto, a estratégia adotada é **não iniciar o projeto de ML
prematuramente**.

Primeiro será construída a infraestrutura dos agentes e coletado um
histórico de dados.

Esse histórico poderá conter, por exemplo:

``` text
data/hora
linha
veículo
ponto
condições climáticas
trânsito
velocidade
tipo de via
atraso anterior
atraso observado
confiança
estimativa fuzzy
resultado real
```

Depois, esse histórico poderá ser utilizado para treinamento.

------------------------------------------------------------------------

# 24. Possível aplicação futura de ML

Com histórico suficiente, poderão ser avaliados modelos como:

-   Regressão Linear;
-   Regressão Linear Múltipla;
-   Random Forest Regressor;
-   Decision Tree;
-   KNN;
-   outros modelos de regressão apropriados ao conjunto de dados.

A finalidade seria descobrir relações existentes nos dados que não
necessariamente foram previstas manualmente pela base fuzzy.

------------------------------------------------------------------------

# 25. Fuzzy + Machine Learning

Uma possibilidade futura é utilizar os dois métodos de forma
complementar.

``` text
             Dados históricos
                    │
                    ▼
             Machine Learning
                    │
                    ▼
             padrão aprendido
                    │
                    ├──────────┐
                    │          │
                    ▼          ▼
              Agentes      Sistema Fuzzy
                    │          │
                    └────┬─────┘
                         ▼
                  Estimativa final
```

Nesse cenário:

-   a lógica fuzzy representa conhecimento explícito;
-   os agentes representam entidades e interações;
-   o Machine Learning aprende padrões a partir dos dados históricos.

Essa arquitetura permite combinar conhecimento especializado e
conhecimento extraído dos dados.

------------------------------------------------------------------------

# 26. Estado atual do projeto

Atualmente, o projeto possui como núcleo funcional:

-   estrutura do sistema fuzzy;
-   variáveis linguísticas;
-   normalização de dados;
-   carregamento de regras por CSV;
-   construção automática das regras;
-   inferência fuzzy;
-   análise das regras ativadas;
-   geração automática de testes;
-   classificação dos resultados;
-   mecanismo de fallback;
-   análise de cobertura;
-   análise de consistência;
-   diagnóstico automatizado da base de regras;
-   identificação de conflitos;
-   identificação de duplicidades;
-   identificação de sobreposições.

A base de regras atual está em processo de refinamento.

------------------------------------------------------------------------

# 27. Próximas etapas

A evolução planejada é:

``` text
[1] Refinamento das regras atuais
          ↓
[2] Validação da base
          ↓
[3] Identificação das lacunas
          ↓
[4] Inclusão controlada de novas regras
          ↓
[5] Modelo de agentes inteligentes
          ↓
[6] Coleta de histórico
          ↓
[7] Construção do dataset
          ↓
[8] Avaliação de modelos de Machine Learning
          ↓
[9] Integração Fuzzy + Agentes + ML
          ↓
[10] Avaliação experimental do modelo
```

------------------------------------------------------------------------

# 28. Contribuição acadêmica

A principal contribuição do projeto está na construção de uma
arquitetura capaz de trabalhar com **incerteza e ausência de informações
diretas de posicionamento**, utilizando diferentes fontes de contexto.

Do ponto de vista metodológico, o projeto permite estudar:

-   sistemas fuzzy;
-   representação de conhecimento;
-   inferência baseada em regras;
-   validação de bases de conhecimento;
-   sistemas multiagentes;
-   integração de dados;
-   normalização;
-   modelagem computacional;
-   aprendizado de máquina;
-   combinação de métodos simbólicos e estatísticos.

Além disso, o módulo de validação permite apresentar experimentalmente
como a qualidade da base de regras é analisada antes da expansão do
sistema.

------------------------------------------------------------------------

# 29. Estrutura conceitual do projeto

Uma estrutura aproximada do projeto é:

``` text
Projeto/
│
├── Fuzzy/
│   ├── fuzzy_system.py
│   ├── knowledge_base.py
│   ├── database.py
│   └── inference_analyzer.py
│
├── Knowledge/
│   └── rule_loader.py
│
├── Validation/
│   ├── coverage.py
│   ├── classifier.py
│   ├── consistency.py
│   └── test_generator.py
│
├── rules.csv
├── diagnostico_validacao.txt
└── main.py
```

A estrutura pode ser reorganizada conforme os próximos módulos forem
implementados.

------------------------------------------------------------------------

# 30. Considerações

O projeto está sendo desenvolvido de maneira incremental.

A prioridade atual é garantir que a **base fuzzy seja coerente,
explicável e suficientemente coberta** antes de introduzir novos níveis
de complexidade.

A introdução de agentes inteligentes será utilizada para estruturar a
dinâmica do sistema e suas entidades.

O Machine Learning será introduzido posteriormente, quando existir
histórico suficiente para que os modelos possam ser treinados e
avaliados de maneira experimental.

Dessa forma, cada etapa do projeto possui uma função clara:

``` text
Fuzzy
→ conhecimento explícito e tratamento da incerteza

Validação
→ verificação da qualidade do conhecimento

Agentes
→ representação das entidades e interações

Histórico
→ geração de dados

Machine Learning
→ descoberta de padrões

Integração
→ modelo computacional completo
```

------------------------------------------------------------------------

## Autor

**Pedro Barbosa de Souza**

Projeto desenvolvido no contexto de Trabalho de Conclusão de Curso
(TCC).
