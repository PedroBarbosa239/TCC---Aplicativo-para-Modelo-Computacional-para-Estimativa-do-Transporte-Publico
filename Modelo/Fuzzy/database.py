import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


class Database:

    def __init__(self):

        # ==========================
        # UNIVERSO DAS VARIÁVEIS
        # ==========================

        self.rain = ctrl.Antecedent(
            np.arange(0, 101, 1),
            "rain"
        )

        self.traffic = ctrl.Antecedent(
            np.arange(0, 101, 1),
            "traffic"
        )

        self.speed = ctrl.Antecedent(
            np.arange(0, 101, 1),
            "speed"
        )

        self.road = ctrl.Antecedent(
            np.arange(0, 101, 1),
            "road"
        )

        self.previous_delay = ctrl.Antecedent(
            np.arange(0, 101, 1),
            "previous_delay"
        )

        self.delay = ctrl.Consequent(
            np.arange(0, 101, 1),
            "delay"
        )

        self.create_membership_functions()

    def create_membership_functions(self):

        # ------------------------------------------------------
        # CHUVA
        # ------------------------------------------------------

        self.rain["none"] = fuzz.trapmf(
            self.rain.universe,
            [0, 0, 10, 25]
        )

        self.rain["light"] = fuzz.trimf(
            self.rain.universe,
            [10, 30, 50]
        )

        self.rain["moderate"] = fuzz.trimf(
            self.rain.universe,
            [40, 60, 80]
        )

        self.rain["heavy"] = fuzz.trapmf(
            self.rain.universe,
            [70, 85, 100, 100]
        )

        # ------------------------------------------------------
        # CONGESTIONAMENTO
        # ------------------------------------------------------

        self.traffic["very_low"] = fuzz.trapmf(
            self.traffic.universe,
            [0, 0, 10, 25]
        )

        self.traffic["low"] = fuzz.trimf(
            self.traffic.universe,
            [10, 25, 40]
        )

        self.traffic["medium"] = fuzz.trimf(
            self.traffic.universe,
            [30, 50, 70]
        )

        self.traffic["high"] = fuzz.trimf(
            self.traffic.universe,
            [60, 75, 90]
        )

        self.traffic["very_high"] = fuzz.trapmf(
            self.traffic.universe,
            [80, 90, 100, 100]
        )

        # ------------------------------------------------------
        # VELOCIDADE
        # (0 = muito rápida)
        # (100 = muito lenta)
        # ------------------------------------------------------

        self.speed["very_fast"] = fuzz.trapmf(
            self.speed.universe,
            [0, 0, 10, 20]
        )

        self.speed["fast"] = fuzz.trimf(
            self.speed.universe,
            [10, 25, 40]
        )

        self.speed["normal"] = fuzz.trimf(
            self.speed.universe,
            [30, 50, 70]
        )

        self.speed["slow"] = fuzz.trimf(
            self.speed.universe,
            [60, 75, 90]
        )

        self.speed["very_slow"] = fuzz.trapmf(
            self.speed.universe,
            [80, 90, 100, 100]
        )

        # ------------------------------------------------------
        # TIPO DA VIA
        # ------------------------------------------------------

        self.road["excellent"] = fuzz.trapmf(
            self.road.universe,
            [0, 0, 10, 20]
        )

        self.road["good"] = fuzz.trimf(
            self.road.universe,
            [10, 25, 40]
        )

        self.road["average"] = fuzz.trimf(
            self.road.universe,
            [30, 50, 70]
        )

        self.road["poor"] = fuzz.trimf(
            self.road.universe,
            [60, 75, 90]
        )

        self.road["very_poor"] = fuzz.trapmf(
            self.road.universe,
            [80, 90, 100, 100]
        )

        # ------------------------------------------------------
        # ATRASO ANTERIOR
        # ------------------------------------------------------

        self.previous_delay["very_early"] = fuzz.trapmf(
            self.previous_delay.universe,
            [0, 0, 10, 20]
        )

        self.previous_delay["early"] = fuzz.trimf(
            self.previous_delay.universe,
            [10, 25, 40]
        )

        self.previous_delay["on_time"] = fuzz.trimf(
            self.previous_delay.universe,
            [35, 50, 65]
        )

        self.previous_delay["late"] = fuzz.trimf(
            self.previous_delay.universe,
            [60, 75, 90]
        )

        self.previous_delay["very_late"] = fuzz.trapmf(
            self.previous_delay.universe,
            [80, 90, 100, 100]
        )

        # ------------------------------------------------------
        # SAÍDA
        # ------------------------------------------------------

        self.delay["very_early"] = fuzz.trapmf(
            self.delay.universe,
            [0, 0, 10, 20]
        )

        self.delay["early"] = fuzz.trimf(
            self.delay.universe,
            [10, 25, 40]
        )

        self.delay["on_time"] = fuzz.trimf(
            self.delay.universe,
            [35, 50, 65]
        )

        self.delay["late"] = fuzz.trimf(
            self.delay.universe,
            [60, 75, 90]
        )

        self.delay["very_late"] = fuzz.trapmf(
            self.delay.universe,
            [80, 90, 100, 100]
        )


    def delay_to_minutes(self, delay_value):
        """
        Converte o índice fuzzy de atraso (0–100)
        para minutos (-4 a +4).

        0   -> -2 min
        25  -> -1 min
        50  ->  0 min
        75  -> +1 min
        100 -> +2 min
        """

        delay_minutes = (float(delay_value) - 50.0) * 0.04

        if abs(delay_minutes) < 0.000001:
            delay_minutes = 0.0

        return delay_minutes