from datetime import datetime
from typing import Dict, Tuple, List

from explorateur import Explorateur, MOVE_RESULT
from hitman.hitman import HitmanReferee, HC
from utils.PriorityQueue import PriorityQueue


class Joueur:
    def __init__(self, debug=False, with_sat=False):
        self.phase_1_res = None
        self.debug = debug
        self.with_sat = with_sat
        self.referre = HitmanReferee()

    def play_phase_1(self):
        start_time = datetime.now()

        init_status = self.referre.start_phase1()
        explo_queue = PriorityQueue()

        total_x = init_status["n"]
        total_y = init_status["m"]

        init_position = init_status["position"]
        init_orientation = init_status["orientation"]

        explorateur = Explorateur(referre=self.referre, init_status=init_status, phase=1, debug=self.debug, with_dimacs=self.with_sat)
        explorateur.print_status(init_status)

        for i in range(total_x):
            for j in range(total_y):
                if (i, j) not in explorateur.cases_connues and i < total_x and j < total_y:
                    explorateur.cases_connues[(i, j)] = -1
                    explo_queue.push((i, j))

        MAP_DISCOVERED = False
        next_to_explore = (0, 0)

        while not MAP_DISCOVERED:
            if explo_queue.isEmpty():
                break

            nouvelle_explo_queue = PriorityQueue()
            explo_path: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}

            while not explo_queue.isEmpty():
                pos = explo_queue.pop()
                if explorateur.cases_connues[pos] == -1:
                    result, path, path_cost = self.get_best_path(explorateur, pos, explorateur.position, explorateur.orientation, False)
                    nouvelle_explo_queue.push(pos, path_cost)
                    explo_path[pos] = path
            explo_queue = nouvelle_explo_queue

            while explorateur.position == next_to_explore or explorateur.cases_connues[next_to_explore] != -1:
                if explo_queue.isEmpty():
                    MAP_DISCOVERED = True
                    break
                next_to_explore = explo_queue.pop()

            if MAP_DISCOVERED:
                break

            print(f"--------------      EXPLORATION-{next_to_explore}      ---------------------")
            explorateur.move_to_goal(goal=next_to_explore, path=explo_path[next_to_explore])
            explorateur.print_map()
            print("-------------------------------------------------------------------")
        explorateur.print_map()

        while not explo_queue.isEmpty():
            pos = explo_queue.pop()
            print(f"NEXT-POS-TO-EXPLORE : {pos}")
        print(f"TOTAL PENALTIES : {explorateur.penalties}")
        print(f"TOTAL MOUVEMENT : {explorateur.moves}")
        print(f"EXPLORED_NODE : {explorateur.explored_node}")
        print(f"EXPLORED_NODE_LENGTH : {len(explorateur.explored_node)}")

        path_cost = explorateur.valuate_path(explorateur.explored_node, init_position, init_orientation)
        print(f"PATH_COST : {path_cost[0]}")

        self.send_map_to_referee(explorateur)
        self.phase_1_res = self.referre.end_phase1()
        del explorateur

    def play_phase_2(self):
        status = self.referre.start_phase2()
        explorateur = Explorateur(referre=self.referre, init_status=status, phase=2, debug=True, with_dimacs=False)

        map_infos = self.phase_1_res[3]

        # init de la map avec les infos de la phase 1
        for pos in self.phase_1_res[3]:
            if self.debug: print(f"CASE : {pos} - {map_infos[pos]}")
            explorateur.cases_connues[pos] = HC(map_infos[pos]).value

        explorateur.print_map()
        print(status)

        guard_values = [HC.GUARD_N.value, HC.GUARD_S.value, HC.GUARD_E.value, HC.GUARD_W.value]
        goals: Dict[HC, Tuple[int, int]] = {}

        for objective in [HC.SUIT.value, HC.PIANO_WIRE.value, HC.TARGET.value]:
            for case in explorateur.cases_connues:
                if explorateur.cases_connues[case] == objective:
                    goals[HC(objective)] = case
        # Récupérer les positions des objectifs

        '''
        0- On suppose de base que la map est explorable i.e il existe toujours un chemin pour atteindre les objectifs principaux (Piano_wire et target), sinon dans le cadre de ce projet, la phase 1 n'a pas de sens. 
        1- Calcul chemin le moins chère en pénalités pour aller vers la piano_wire puis costume puis target - PATH 1
        2- Calcul chemin le moins chère en pénalités pour aller vers le costume puis piano_wire puis target - PATH 2
        3- Calcul chemin le moins chère en pénalités pour aller vers la piano_wire puis target - PATH 3
        4- Vérification de l'existence d'un des cas puis choix de la meilleure option (la moins chère)
        4.bis - Vérifier si target est regardé par un garde, si target regardé par un garde alors voir si le coût costume serait moins cher ?
        6- Si garde regarde vers target, l'éliminer coutriat moins chère ?
        4- Calcul chemin en pénalités pour aller depuis target vers (0, 0)
        '''

        init_position = status["position"]
        init_orientation = status["orientation"]

        #  1- Calcul chemin le moins chère en pénalités pour aller vers la piano_wire puis costume puis target - PATH 1

        strategys = self.get_best_strategy(init_position, init_orientation, explorateur, goals)
        strategy_cost = None
        strategy_obj = []
        strategy_path = []
        for strategy in strategys:
            temp_strategy_cost, temp_strategy, strategy_path = strategys[strategy]
            print(f"STRATEGY : {strategy} - {temp_strategy_cost} - {temp_strategy}")
            if strategy_cost is None or strategy_cost > temp_strategy_cost:
                strategy_cost = temp_strategy_cost
                strategy_obj = temp_strategy
        print(f"STRATEGY CHOSEN : {strategy_cost} - {strategy_obj}")
        print(f"GLOBAL CHOSEN PATH : {strategy_path}")

        for path_key in strategy_path:
            path = strategy_path[path_key]
            explorateur.move_to_goal(goal=path_key, path=path)
            if explorateur.cases_connues[explorateur.position] == HC.PIANO_WIRE.value:
                self.referre.take_weapon()
            if explorateur.cases_connues[explorateur.position] == HC.SUIT.value:
                self.referre.take_suit()
                self.referre.put_on_suit()
            if explorateur.cases_connues[explorateur.position] == HC.TARGET.value:
                self.referre.kill_target()

        status = self.referre.end_phase2()
        print(f"STRATEGY CHOSEN : {strategy_cost} - {strategy_obj}")
        explorateur.print_map()
        print(status)
        print(self.phase_1_res)
        del explorateur

    def get_best_strategy(self, current_position, current_orientation, explorateur,
                          goals_pos: Dict[HC, Tuple[int, int]]) -> Dict[
        int, Tuple[int, List[HC], Dict[Tuple[int, int], List[Tuple[int, int]]]]]:
        goals: Dict[int, List[HC]] = {1: [HC.PIANO_WIRE, HC.SUIT, HC.TARGET, (0, 0)],
                                      2: [HC.SUIT, HC.PIANO_WIRE, HC.TARGET, (0, 0)],
                                      3: [HC.PIANO_WIRE, HC.TARGET, (0, 0)]}
        path_costs: Dict[int, Tuple[int, List[HC], Dict[Tuple[int, int], List[Tuple[int, int]]]]] = {}
        for g_plan in goals:
            plan_key, plan = g_plan, goals[g_plan]
            temp_path: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}

            total_cost = 0
            suit_on = False
            status = MOVE_RESULT.GOAL_REACHED

            for objective in plan:
                objective_pos = objective
                if objective != (0, 0):
                    objective_pos = goals_pos[objective]
                result, path, path_cost = self.get_best_path(explorateur, objective_pos, current_position,
                                                             current_orientation,
                                                             suit_on)
                temp_path[objective_pos] = path
                if result == MOVE_RESULT.UNREACHABLE_GOAL and (
                        objective == (0, 0) or (objective == HC.TARGET or objective == HC.SUIT)):
                    status = MOVE_RESULT.UNREACHABLE_GOAL
                    break
                if objective == HC.SUIT:
                    suit_on = True
                current_position = objective_pos
                total_cost += path_cost
            if self.debug: print(f"PLAN : {plan_key} - {total_cost} - {plan} - {temp_path}")
            path_costs[plan_key] = total_cost, plan, temp_path if status != MOVE_RESULT.UNREACHABLE_GOAL else None
        return path_costs

    def get_best_path(self, explorateur: Explorateur, goal: Tuple[int, int], init_position: Tuple[int, int],
                      init_orientation: HC, suit_on: bool) -> Tuple[
        MOVE_RESULT, List[Tuple[int, int]], int]:
        temp_path = explorateur.search_a_star_sauvgarde_etat(goal=goal,
                                                             successor=explorateur.get_safe_succ,
                                                             current_pos=init_position,
                                                             current_orientation=init_orientation)
        temp_path_2 = explorateur.search_a_star_sauvgarde_etat(goal=goal,
                                                               successor=explorateur.get_succ,
                                                               current_pos=init_position,
                                                               current_orientation=init_orientation)
        if temp_path[0] is None and temp_path_2[0] is None:
            return MOVE_RESULT.UNREACHABLE_GOAL, [], 0
        temp_chemin = explorateur.reconstruire_chemin(temp_path[1], init_position, goal) if temp_path[
                                                                                                0] is not None else []
        temp_chemin_2 = explorateur.reconstruire_chemin(temp_path_2[1], init_position, goal) if temp_path_2[
                                                                                                    0] is not None else []

        path_1_cost, _ = explorateur.valuate_path(temp_chemin,
                                                  init_pos=init_position,
                                                  init_orientation=init_orientation,
                                                  suit_on=suit_on
                                                  )
        path_2_cost, _ = explorateur.valuate_path(temp_chemin_2,
                                                  init_pos=init_position,
                                                  init_orientation=init_orientation,
                                                  suit_on=suit_on
                                                  )

        if len(temp_chemin) == 0 or path_1_cost > path_2_cost:
            temp_chemin = temp_chemin_2
            path_1_cost = path_2_cost
        return MOVE_RESULT.GOAL_REACHED, temp_chemin, path_1_cost

    def send_map_to_referee(self, explorateur: Explorateur):
        map_info = explorateur.get_map_infos_for_referee()
        self.referre.send_content(map_info)

    def print_res(self, res):
        print("-------------------------------------------------------------------")
        for var in res:
            print(f"\t{var}")
        print("-------------------------------------------------------------------")
