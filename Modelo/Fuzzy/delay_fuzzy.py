import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

from .knowledge_base import KnowledgeBase
from .database import Database


class DelayFuzzySystem:

    def __init__(self):
        
        # ==========================
        # UNIVERSO DAS VARIÁVEIS
        # ==========================

        self.database = Database()

        self.rain = self.database.rain
        self.traffic = self.database.traffic
        self.speed = self.database.speed
        self.road = self.database.road
        self.previous_delay = self.database.previous_delay
        self.delay = self.database.delay

        self.knowledge = KnowledgeBase(self)
        self.build_system()

        
    # ==========================================================
    # VISUALIZAÇÃO
    # ==========================================================

    def show_memberships(self):

        self.rain.view()
        self.traffic.view()
        self.speed.view()
        self.road.view()
        self.previous_delay.view()
        self.delay.view()


    def create_rules(self):
        return self.knowledge.create_rules()

    def build_system(self):

        rules = self.create_rules()

        print(f"{len(rules)} regras carregadas.")

        # Analisa a base de regras - habilita somente quando for fazer testes
        #self.knowledge.analyze_rules()

        self.control_system = ctrl.ControlSystem(rules)

        self.simulation = ctrl.ControlSystemSimulation(
            self.control_system
        )

    def compute(self, context):

       
        self.simulation.input["rain"] = context["rain"]
        self.simulation.input["traffic"] = context["traffic"]
        self.simulation.input["speed"] = context["speed"]
        self.simulation.input["road"] = context["road_flow"]

        print("\n==============================")
        print("CONTEXTO")
        print("==============================")
        print(context)

        variables = [
            ("RAIN", self.rain, context["rain"]),
            ("TRAFFIC", self.traffic, context["traffic"]),
            ("ROAD", self.road, context["road_flow"]),
            ("SPEED", self.speed, context["speed"])
        ]

        for name, variable, value in variables:

            print(f"\n{name} = {value}")

            for term in variable.terms:

                degree = fuzz.interp_membership(
                    variable.universe,
                    variable[term].mf,
                    value
                )

                print(
                    f"{term:<12} -> {degree:.3f}"
                )

        # ==================================================
        # VERIFICAR ATIVAÇÃO DAS REGRAS
        # ==================================================

        activated_rules = []

        print("\n==============================")
        print("ATIVAÇÃO DAS REGRAS")
        print("==============================")

        for rule in self.knowledge.rules:

            values = []

            for condition in rule["conditions"]:

                variable_name = condition["variable"]
                term = condition["term"]

                if variable_name == "Rain":
                    variable = self.rain
                    value = context["rain"]

                elif variable_name == "Traffic":
                    variable = self.traffic
                    value = context["traffic"]

                elif variable_name == "Road":
                    variable = self.road
                    value = context["road_flow"]

                elif variable_name == "Speed":
                    variable = self.speed
                    value = context["speed"]

                mu = fuzz.interp_membership(
                    variable.universe,
                    variable[term].mf,
                    value
                )

                values.append(mu)

            activation = min(values)

            print(
                f'{rule["id"]:<5} '
                f'-> {activation:.3f} '
                f'({rule["output"]})'
            )

            if activation > 0:

                activated_rules.append({
                    "id": rule["id"],
                    "output": rule["output"],
                    "activation": activation
                })

        # ==================================================
        # NENHUMA REGRA ATIVADA
        # ==================================================

        if not activated_rules:

            print("\n==============================")
            print("FALLBACK")
            print("==============================")

            print(
                "Nenhuma regra fuzzy foi ativada."
            )

            print(
                "Aplicando valor neutro: 50.0"
            )

            return {
                "delay": 50.0,
                "delay_minutes": self.database.delay_to_minutes(delay_fuzzy),
                "fallback": True,
                "activated_rules": []
            }

        # ==================================================
        # INFERÊNCIA FUZZY
        # ==================================================

        try:

            self.simulation.compute()

            print("\nSaída da simulação:")
            print(self.simulation.output)

            delay_fuzzy = float(self.simulation.output["delay"])

            delay_minutes = self.database.delay_to_minutes(
                delay_fuzzy
            )

            return {
                "delay": delay_fuzzy,
                "delay_minutes": delay_minutes,
                "fallback": False,
                "activated_rules": activated_rules
            }

        except Exception as e:

            print("\n==============================")
            print("ERRO NA INFERÊNCIA")
            print("==============================")

            print("Contexto:")
            print(context)

            print("Output:")
            print(self.simulation.output)

            raise e
