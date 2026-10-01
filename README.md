# TCC - Computational Model for Public Transport Estimation

This repository contains the source code for a computational model designed to estimate public transport vehicle delays, developed as a Final Course Project (TCC). The system leverages a combination of Fuzzy Logic, an Agent-Based Model, and external APIs to produce delay estimates even in scenarios with incomplete or unavailable GPS data.

## Overview

Traditional public transport tracking systems rely heavily on real-time GPS data. This project addresses situations where such data is unreliable or absent due to signal loss, communication delays, or outdated information.

The model uses indirect evidence from the environment to infer the vehicle's behavior. By combining factors like weather conditions, traffic intensity, road characteristics, and vehicle speed, the system estimates the likelihood and magnitude of a delay.

The core components include:
-   **Fuzzy Logic Engine**: To handle uncertainty and reason with linguistic variables (e.g., "heavy traffic," "light rain").
-   **Agent-Based Model**: To simulate the public transport network, where each bus stop is an intelligent agent that processes and propagates information.
-   **Data Normalization**: To convert heterogeneous data from external APIs into a uniform format for the fuzzy system.
-   **Validation Framework**: A comprehensive suite to ensure the logical consistency and coverage of the knowledge base.
-   **Real-time Monitoring GUI**: A Tkinter application to visualize the simulation, track buses on a map, and query arrival times.

## System Architecture

The project is built with a modular and incremental architecture. The main data flow is as follows:

```text
               ┌──────────────────────┐
               │   External APIs      │
               │ (Weather, Traffic)   │
               └──────────┬───────────┘
                          │
                          ▼
               ┌──────────────────────┐
               │  Data Normalization  │
               │ (0-100 Unified Scale)│
               └──────────┬───────────┘
                          │
                          ▼
               ┌──────────────────────┐
               │  Fuzzy Logic System  │
               │  (Knowledge Base)    │
               └──────────┬───────────┘
                          │
                          ▼
        ┌──────────────────────────────────┐
        │        Agent-Based Model         │
        │ (BusStopAgent, AgentNetwork)     │
        └──────────┬────────────┬──────────┘
                   │            │
                   ▼            ▼
   ┌──────────────────────┐  ┌────────────────────┐
   │ Real-time Simulation │  │ Controlled Analysis│
   │  (GUI Application)   │  │ (Simulation Script)│
   └──────────────────────┘  └────────────────────┘
```

## Key Features

### Fuzzy Inference Engine

The core of the estimation logic is a `scikit-fuzzy` based system.

-   **Linguistic Variables**: The model uses several antecedent (input) variables (`Rain`, `Traffic`, `Road`, `Speed`) and one consequent (output) variable (`Delay`). Each variable has defined linguistic terms (e.g., `very_low`, `low`, `medium`, `high`, `very_high` for `Traffic`).
-   **Knowledge Base**: The intelligence of the system is stored in a `rules.csv` file, separating the domain knowledge from the application code. This allows for easy modification and expansion of the rule set. A `KnowledgeBase` class dynamically loads and builds these rules.

    *Example Rule:*
    ```csv
    ID,Grupo,Rain,Traffic,Road,Speed,Delay,Justificativa,Implementada
    A01,A,heavy,high,,,very_late,"Chuva intensa combinada com trânsito alto caracteriza forte atraso.",TRUE
    ```
-   **Fallback Mechanism**: If no rules are significantly activated for a given context, the system defaults to a neutral output (`on_time`) to ensure a predictable response, preventing inference errors.

### Agent-Based Simulation Model

The transport network is modeled as a system of intelligent agents.

-   **`BusStopAgent`**: Each bus stop is represented by an agent that can receive messages, process trips, and update its state. It combines the estimated delay received from the previous agent with its own local fuzzy inference.
-   **`AgentNetwork`**: Manages the collection of agents and the connections between them, forming the bus routes.
-   **`AgentMessage`**: A data structure used for communication between agents, carrying information like departure/arrival times, estimated delay, and confidence levels.
-   **`TripManager`**: Orchestrates the entire simulation, creating and updating trips based on a schedule (`schedules.csv`) and the system clock.

### Comprehensive Validation Suite

A robust validation framework, located in the `Validation/` directory, ensures the quality and logical soundness of the fuzzy knowledge base.

-   **`TestGenerator`**: Automatically creates a suite of test cases by generating a representative input context for each rule in `rules.csv`.
-   **`ConsistencyAnalyzer`**: Checks the rule base for logical flaws before execution, identifying:
    -   **Conflicts**: Rules with identical conditions but different outcomes.
    -   **Duplicates**: Identical rules.
    -   **Subsumption**: A general rule that overlaps with a more specific one.
-   **`CoverageAnalyzer`**: Tracks which rules were activated during tests, helping to identify unused rules and gaps in the knowledge base.
-   **`diagnostico_validacao.txt`**: A detailed report file is generated after each validation run, containing the consistency analysis, test-by-test results, activated rules for each test, and a final coverage report.

### Controlled Simulation & Analysis

The script `simulacao_controlada_8_pontos_alterada (1).py` runs a deterministic simulation across a route of 8 stops and 7 predefined scenarios. This allows for controlled experiments, such as comparing the system's output with different kinematic parameters (e.g., speed factor of 1.0 vs. 0.9).

The results, including detailed segment-by-segment data, plots, and a summary report, are saved to the `resultados_simulacao_8_pontos/` directory.

### Real-Time Monitoring GUI

The `Interface/app_monitoramento_linha.py` script launches a Tkinter-based graphical user interface for visualizing the simulation.

-   **Map View**: Displays bus routes, stop markers, and real-time animated bus positions using `tkintermapview`.
-   **Line Status**: Shows which buses are active on a selected route, their current/next stop, and the estimated delay.
-   **Arrival Queries**: Allows users to select a line and a stop to get a real-time arrival prediction for all active buses.
-   **Automatic Updates**: The `TripManager` drives the simulation in the background, and the GUI refreshes periodically to reflect the current state of the transport network.

## Project Structure

```
Modelo/
├── Agents/            # Agent-Based Model (BusStopAgent, AgentNetwork)
├── Api/               # Wrappers for external APIs (Weather, Traffic, etc.)
├── Data/              # Data loaders and static CSV files (stops, routes, schedules)
├── Fuzzy/             # Core Fuzzy Logic implementation (DelayFuzzySystem, KnowledgeBase)
├── Interface/         # Tkinter GUI application for real-time monitoring
├── Knowledge/         # Rule loader and the `rules.csv` knowledge base
├── Normalization/     # Logic for normalizing heterogeneous input data
├── Schedules/         # Schedule loader for trip departure times
├── Services/          # High-level services (TripManager, ContextService)
├── Simulation/        # Core simulation logic (BusSimulation)
├── Validation/        # Validation framework (Consistency, Coverage, Test Generation)
├── main_validation.py # Script to run the validation suite
└── simulacao_controlada_8_pontos_alterada (1).py # Script for controlled analysis
```

## How to Run

### 1. Validation

To analyze the fuzzy rule base for consistency and run the automated test suite, execute the main validation script. This will generate a detailed `diagnostico_validacao.txt` report.

```bash
python Modelo/main_validation.py
```

### 2. Controlled Simulation

To run the controlled 8-stop simulation and generate analysis files (CSV reports, plots), execute the simulation script.

```bash
python Modelo/simulacao_controlada_8_pontos_alterada (1).py
```
The output will be saved in the `Modelo/resultados_simulacao_8_pontos/` directory.

### 3. GUI Application

To launch the real-time monitoring application, run the `app_monitoramento_linha.py` script.

```bash
python Modelo/Interface/app_monitoramento_linha.py
```

## Future Work

-   **Refine Rule Base**: Continue to refine and expand the fuzzy `rules.csv` based on validation results and simulation analysis to cover more scenarios.
-   **Historical Data Collection**: Implement a mechanism to log simulation data (contexts, fuzzy outputs, real outcomes) to build a historical dataset.
-   **Machine Learning Integration**: Use the collected dataset to train Machine Learning models (e.g., Random Forest, Gradient Boosting) to discover patterns not explicitly captured by the fuzzy rules.
-   **Hybrid Model**: Combine the strengths of the explicit knowledge in the fuzzy system with the data-driven patterns from the ML models to create a more accurate and robust hybrid estimation system.
