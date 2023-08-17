import math
import random
from enum import Enum
from typing import List, Tuple, Dict, Callable, Optional

from dimacs import Dimacs
from hitman.hitman import HitmanReferee, HC
from utils.PriorityQueue import PriorityQueue


class MOVE_RESULT(Enum):
    GOAL_REACHED = 1,
    CASE_IN_PATH_NOT_SAFE = 2,
    UNREACHABLE_GOAL = 3,


class Explorateur:
    def __init__(self, referre: HitmanReferee, init_status: Dict, phase: int, debug: bool = False,
                 with_dimacs: bool = False):
        self.referre = referre
        self.total_x: int = init_status["n"]
        self.total_y: int = init_status["m"]
        self.position: Tuple[int, int] = init_status["position"]
        self.orientation = init_status["orientation"]
        self.penalties: int = 0
        self.noise: int = 0
        self.old_penalties: int = 0
        self.moves: int = 0
        self.explored_node = [(0, 0)]
        self.cases_connues: Dict[Tuple[int, int], int] = {}
        self.phase = phase
        self.use_dimacs = with_dimacs
        if self.phase == 1 and with_dimacs:
            self.dimacs = Dimacs(init_status)

        # ADD DEBUG VAR
        self.debug = debug
        # Ajout condition initale.
        self.add_case_connue_vision([(self.position, HC.EMPTY)])
        self.add_case_connue_vision(init_status["vision"])
        self.translation_dict: Dict[HC, HC] = {HC.E: HC.GUARD_E, HC.W: HC.GUARD_W, HC.N: HC.GUARD_N,
                                                  HC.S: HC.GUARD_S}

    def search_a_star_sauvgarde_etat(self, goal: Tuple[int, int],
                                     successor: Callable[[Tuple[int, int]], List[Tuple[
                                         int, int]]], current_pos: Tuple[int, int] = None,
                                     current_orientation: HC = None, ):  # Rechere A* avec sauvegarde des états & de leur parents
        if current_pos is None:
            current_pos = self.position
        if current_orientation is None:
            current_orientation = self.orientation

        frontier = PriorityQueue()
        frontier.push(current_pos, self.heuristique_manhattan(current_pos, goal))
        save = {current_pos: None}
        start_pos = current_pos

        while not frontier.isEmpty():
            current_state = frontier.pop()
            for temp in successor(current_state):
                if temp not in save:
                    save[temp] = current_state
                    if goal == temp:
                        return temp, save
                    state_add_infos = self.get_move_needed(current_state, current_orientation, goal)
                    current_orientation = state_add_infos[1]
                    heursitique = self.heuristique_manhattan(temp, goal) + state_add_infos[0] + self.reconstruire_chemin(save, start_pos, temp).__len__()
                    frontier.push(temp, heursitique)
        return None, save

    def reconstruire_chemin(self, came_from: Dict[Tuple[int, int], Tuple[int, int]],
                            start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        current: Tuple[int, int] = goal
        path: list[Tuple[int, int]] = []
        if goal not in came_from:  # no path was found
            return []
        while current != start:
            path.append(current)
            current = came_from[current]
        path.append(start)
        path.reverse()
        return path

    def heuristique_manhattan(self, init: Tuple[int, int], goal: Tuple[int, int]) -> float:
        return math.sqrt((goal[0] - init[0]) ** 2 + (goal[1] - init[1]) ** 2)

    def get_path(self, goal: Tuple[int, int], safe_path: bool, start: Tuple[int, int] = None,
                 init_orientation: HC = None) -> Tuple[List[Tuple[int, int]], float]:
        if start is None:
            start = self.position
        if init_orientation is None:
            init_orientation = self.orientation
        if safe_path:
            path = self.search_a_star_sauvgarde_etat(goal=goal, successor=self.get_safe_succ, current_pos=start,
                                                     current_orientation=init_orientation)
        else:
            path = self.search_a_star_sauvgarde_etat(goal=goal, successor=self.get_succ, current_pos=start,
                                                     current_orientation=init_orientation)
        chemin = self.reconstruire_chemin(path[1], start, goal)
        path_cost = self.valuate_path(chemin, start, init_orientation)[0]
        if len(chemin) > 0:
            return chemin, path_cost
        else:
            return [], float("inf")

    def move_to_goal(self, goal: Tuple[int, int], path: List[Tuple[int, int]] = None) -> \
            Tuple[bool, MOVE_RESULT]:
        try_to_reach = True
        while try_to_reach:
            self.decouvrir_voisins()

            if self.position == goal and self.phase == 1 and self.cases_connues[self.position] != -1:
                try_to_reach = False
                return True, MOVE_RESULT.GOAL_REACHED

            self.print_map()

            for i in range(0, len(path)):
                case = path[i]
                if self.position == goal and self.phase == 2:
                    try_to_reach = False
                    return True, MOVE_RESULT.GOAL_REACHED
                if case == goal and self.phase == 1 and self.cases_connues[case] != -1:
                    try_to_reach = False
                    return True, MOVE_RESULT.GOAL_REACHED
                if case != self.position:
                    rotation = ""
                    while rotation != "MOVE_FORWARD":
                        rotation = \
                            self.obtenir_orientation(current_position=self.position,
                                                     current_orientation=self.orientation,
                                                     goal=case)[
                                0]
                        self.trun_to_direction(goal=case)
                        if self.debug: print(f"ROTATION : {rotation}")

                    if not self.is_case_safe(case):
                        self.print_map()
                        print("CASE_NOT_SAFE")
                        return False, MOVE_RESULT.CASE_IN_PATH_NOT_SAFE
                    else:
                        ## IE BOUGER PROCHAINE CASE SAFE
                        if self.debug:
                            print(f"-------- DEBUG : CURRENT-POS : {self.position}")
                            print(f"-------- DEBUG : CURRENT-ORI : {self.orientation}")
                            print(f"-------- DEBUG : ACTUAL-TARGET : {case}")
                            print(f"-------- DEBUG : CURRENT-CHEMIN : {goal}")

                        status = self.referre.move()

                        self.moves += 1
                        self.old_penalties = self.penalties
                        self.position = status["position"]
                        self.orientation = status["orientation"]
                        self.add_case_connue_vision(status["vision"])
                        self.penalties = status["penalties"]
                        self.is_guard_possible(status=status)
                        self.noise = status["hear"]

                        self.explored_node.append(self.position)
                        if self.debug: self.print_status(status)

                        if "Err: invalid move" in status["status"]:
                            print("GAME OVER")
                            self.print_map()
                            raise Exception("INVALID MOVE - OVER")

                        self.decouvrir_voisins()

                        if self.phase == 1 and self.use_dimacs:
                            self.dimacs.handle_noise(status)
                            if i + 1 >= 0 and i+1 < len(path):
                                case_next = path[i + 1]
                                possible_guard_pos, _ = self.get_guard_possible_cells(position=case_next)
                                if self.debug :
                                    print(f"\t CASE NEXT : {case_next}")
                                    print(f"\t POSSIBLE GUARDS POS : {possible_guard_pos}")
                                result = self.dimacs.test_is_cell_safe(self.cases_connues, status["hear"], self.position, possible_guard_pos)
                                if result[0]:
                                    # garde trouvé en result [1]
                                    guard_orientation: HC = self.get_offest_from_dir(case_next, result[1])
                                    guard_type: HC = self.translation_dict[guard_orientation]
                                    self.cases_connues[result[1]] = guard_type.value

            if self.phase == 1:
                if self.cases_connues[goal] == -1:
                    return False, MOVE_RESULT.UNREACHABLE_GOAL
                else:
                    return True, MOVE_RESULT.GOAL_REACHED

    def valuate_path(self, path: list[Tuple[int, int]], init_pos: Tuple[int, int], init_orientation: HC,
                     suit_on: bool = False) -> Tuple[int, HC]:
        penalties = 0
        current_pos = init_pos
        current_orientation = init_orientation

        for case in path:
            if case != current_pos:
                rotation = ""
                while rotation != "MOVE_FORWARD":
                    rotation = \
                        self.obtenir_orientation(current_position=current_pos,
                                                 current_orientation=current_orientation,
                                                 goal=case)
                    if rotation[0] != "MOVE_FORWARD":
                        current_orientation = rotation[1]
                        if rotation[0] == "DOUBLE_TURN_CLOCKWISE":
                            penalties += 1
                        penalties += 1

                        watched_by_guard = self.is_guard_watching_case(case)
                        if not suit_on:
                            penalties += 5 * watched_by_guard
                    rotation = rotation[0]

                if not self.is_case_safe(case):
                    print("CASE_NOT_SAFE")
                    raise Exception("CASE_NOT_SAFE_IN_VALUATION")
                else:
                    offset_x, offset_y = self.__get_offset(current_orientation)
                    x, y = current_pos

                    watched_by_guard = self.is_guard_watching_case(case)
                    if not suit_on:
                        penalties += 5 * watched_by_guard

                    penalties += 1
                    current_pos = x + offset_x, y + offset_y
        return penalties, current_orientation

    def decouvrir_voisins(self, debug=False):
        discovery_order: Dict[int, List[Tuple[int, int]]] = {}

        voisNord = [(0, 1), (0, 2), (0, 3)]
        voisEst = [(1, 0), (2, 0), (3, 0)]
        voisSouth = [(0, -1), (0, -2), (0, -3)]
        voisWest = [(-1, 0), (-2, 0), (-3, 0)]

        if self.orientation == HC.N:
            discovery_order = {0: voisNord, 1: voisEst, 2: voisSouth, 3: voisWest}
        elif self.orientation == HC.S:
            discovery_order = {0: voisSouth, 1: voisEst, 2: voisNord, 3: voisWest}
        elif self.orientation == HC.E:
            discovery_order = {0: voisEst, 1: voisNord, 2: voisWest, 3: voisSouth}
        elif self.orientation == HC.W:
            discovery_order = {0: voisWest, 1: voisNord, 2: voisEst, 3: voisSouth}

        for i in range(4):
            voisins = discovery_order[i]
            for j in range(3):
                x, y = voisins[j]
                if 0 <= j - 2 < len(voisins):
                    pos_to_study = (self.position[0] + voisins[j - 2][0], self.position[1] + voisins[j - 2][1])
                    if pos_to_study in self.cases_connues and (
                            self.cases_connues[pos_to_study] != -1 or self.cases_connues[
                        pos_to_study] != HC.EMPTY.value):
                        break
                if 0 <= j - 1 < len(voisins):
                    pos_to_study = (self.position[0] + voisins[j - 1][0], self.position[1] + voisins[j - 1][1])
                    if pos_to_study in self.cases_connues and (
                            self.cases_connues[pos_to_study] != -1 or self.cases_connues[
                        pos_to_study] != HC.EMPTY.value):
                        break
                pos_to_study = (self.position[0] + x, self.position[1] + y)
                if pos_to_study in self.cases_connues and self.cases_connues[pos_to_study] == -1:
                    self.trun_to_direction(goal=pos_to_study)

    def get_succ(self, pos_actuelle: Tuple[int, int]) -> List[Tuple[int, int]]:
        succ = []
        for (i, j) in [(0, 1), (1, 0), (-1, 0), (0, -1)]:  # HAUT BAS GAUCHE DROITE
            if 0 <= pos_actuelle[0] + i < self.total_x and 0 <= pos_actuelle[1] + j < self.total_y:
                pos_to_study = (pos_actuelle[0] + i, pos_actuelle[1] + j)
                if pos_to_study in self.cases_connues and self.is_case_safe(pos_to_study):
                    if pos_to_study not in succ:
                        succ.append(pos_to_study)
        return succ

    def get_safe_succ(self, pos_actuelle: Tuple[int, int]) -> List[Tuple[int, int]]:
        succ = []
        for (i, j) in [(0, 1), (1, 0), (-1, 0), (0, -1)]:  # HAUT BAS GAUCHE DROITE
            if 0 <= pos_actuelle[0] + i < self.total_x and 0 <= pos_actuelle[1] + j < self.total_y:
                pos_to_study = (pos_actuelle[0] + i, pos_actuelle[1] + j)
                if pos_to_study in self.cases_connues and (self.is_case_in_path_without_penalities(pos=pos_to_study) or (
                        self.is_case_safe(pos_to_study) != -1 and self.is_guard_watching_case(pos_to_study) in [HC.CIVIL_N.value, HC.CIVIL_W.value, HC.CIVIL_S.value, HC.CIVIL_E.value]
                )):
                    if pos_to_study not in succ:
                        succ.append(pos_to_study)
        return succ

    def is_case_safe(self, pos: Tuple[int, int]):
        if pos in self.cases_connues and self.cases_connues[pos] != HC.WALL.value and \
                self.cases_connues[pos] != HC.GUARD_N.value and \
                self.cases_connues[pos] != HC.GUARD_S.value and \
                self.cases_connues[pos] != HC.GUARD_E.value and \
                self.cases_connues[pos] != HC.GUARD_W.value:
            return True
        return False

    def is_case_in_path_without_penalities(self, pos: Tuple[int, int]):
        if self.is_case_safe(pos):
            return self.is_guard_watching_case(pos) == 0
        return False

    def is_guard_watching_case(self, pos: Tuple[int, int]):
        _, guards = self.get_guard_possible_cells(pos)
        return len(guards)

    # Renvoi un Tuple avec les positions possibles et les positions des gardes qui voient la position
    def get_guard_possible_cells(self, position: Tuple[int, int]) -> Tuple[
        List[Tuple[int, int]], List[Tuple[int, int]]]:
        pos_possible = []
        pos_guard = []
        positions_possible = [(-1, 0), (-2, 0), (1, 0), (2, 0), (0, -1), (0, -2), (0, 1), (0, 2)]
        translation_dict: Dict[HC, HC] = {HC.E: HC.GUARD_E, HC.W: HC.GUARD_W, HC.N: HC.GUARD_N,
                                          HC.S: HC.GUARD_S}

        for i in range(len(positions_possible)):
            pos = position[0] + positions_possible[i][0], position[1] + positions_possible[i][1]
            if 0 <= i - 1 < len(positions_possible) and (
                    pos[0] == positions_possible[i - 1][0] or pos[1] == positions_possible[i - 1][1]):
                # on est sur une case avt - vérifier si y a pas un objet dessus qui bloque la vue si c'est le cas pas besoin de traiter le cas car le garde ne peut pas nous voir.
                pos_avt = positions_possible[i - 1]
                if pos_avt in self.cases_connues and (
                        self.cases_connues[pos_avt] != HC.EMPTY.value or self.cases_connues[pos_avt] != -1):
                    # Le garde ne peut pas nous voir de cette position car il est bloqué par un objet. Si la case avant est inconnue il peut nous voir
                    continue
            if pos in self.cases_connues and self.cases_connues[pos] != -1:
                guard_orientation: HC = self.get_offest_from_dir(position, pos)
                guard_type: HC = translation_dict[guard_orientation]
                if self.cases_connues[pos] == guard_type.value:
                    pos_guard.append(pos)
            if pos in self.cases_connues and self.cases_connues[pos] == -1:
                pos_possible.append(pos)
        return pos_possible, pos_guard

    def get_visible_cells(self, position: Tuple[int, int]) -> List[Tuple[int, int]]:
        pos_visible = []
        positions_possible = [(-3, 0),(-2, 0), (-1, 0), (3, 0), (2, 0), (1, 0), (0, -3), (0, -2), (0, -1), (0, 3), (0, 2), (0, 1) ]

        for i in range(len(positions_possible)):
            pos = position[0] + positions_possible[i][0], position[1] + positions_possible[i][1]
            if 0 <= i - 2 < len(positions_possible) and (
                    pos[0] == positions_possible[i - 2][0] or pos[1] == positions_possible[i - 2][1]):
                # on est sur une case avt - vérifier si n'y a pas un objet dessus qui bloque la vue si c'est le cas pas besoin de traiter le cas car le garde ne peut pas nous voir.
                pos_avt = (positions_possible[i - 2][0] + position[0], positions_possible[i - 2][1] + position[1])
                if pos_avt in self.cases_connues and (
                        self.cases_connues[pos_avt] != HC.EMPTY.value or self.cases_connues[pos_avt] != -1):
                    # Le garde ne peut pas nous voir de cette position car il est bloqué par un objet. Si la case avant est inconnue il peut nous voir
                    continue
            if 0 <= i - 1 < len(positions_possible) and (
                    pos[0] == positions_possible[i - 1][0] or pos[1] == positions_possible[i - 1][1]):
                # on est sur une case avt - vérifier si il n'y a pas un objet dessus qui bloque la vue si c'est le cas pas besoin de traiter le cas car le garde ne peut pas nous voir.
                pos_avt = (positions_possible[i - 2][0] + position[0], positions_possible[i - 2][1] + position[1])
                if pos_avt in self.cases_connues and (
                        self.cases_connues[pos_avt] != HC.EMPTY.value or self.cases_connues[pos_avt] != -1):
                    # Le garde ne peut pas nous voir de cette position car il est bloqué par un objet. Si la case avant est inconnue il peut nous voir
                    continue
            if pos in self.cases_connues and (
                    self.cases_connues[pos] == HC.EMPTY.value or self.cases_connues[pos] == -1):
                # Le garde ne peut pas nous voir de cette position car il est bloqué par un objet. Si la case avant est inconnue il peut nous voir
                pos_visible.append(pos)
        return pos_visible

    def is_guard_possible(self, status):
        if self.penalties - self.old_penalties > 5:
            # Garde possible qui regarde, on doit découvrir les positions où il peut être
            guard_seen_by = (self.penalties - self.old_penalties) % 5
            unknown_guards_positions, guards_watching = self.get_guard_possible_cells(self.position)

            if len(guards_watching) > 0:
                guard_seen_by -= len(guards_watching)

            if guard_seen_by > 0:
                if len(unknown_guards_positions) == 1:
                    # Forcément un guard dans cette position qui regarde vers moi
                    guard_orientation: HC = self.get_offest_from_dir(self.position, unknown_guards_positions[0])
                    guard_type: HC = self.translation_dict[guard_orientation]
                    self.cases_connues[unknown_guards_positions[0]] = guard_type.value
                    if self.debug:
                        print(f"\tPOSITION : {self.position}")
                        self.print_map()
                    guard_offset = self.get_offset(guard_orientation)
                    for i in [1, 2]:
                        guard_possible_look_pos = self.position[0] + (-guard_offset[0] * i), self.position[1] + (
                                -guard_offset[1] * i)
                    print("------------------------------------------------------")
                    return None
                if len(unknown_guards_positions) > 0 and self.use_dimacs:
                    # On choisit un random et on regarde vers lui
                    rand_idx = random.randrange(len(unknown_guards_positions))
                    orientation = self.obtenir_orientation(self.position, self.orientation, unknown_guards_positions[rand_idx])
                    self.trun_to_direction(unknown_guards_positions[rand_idx])
                    self.orientation = orientation[1]
                    self.dimacs.add_possible_guard_in_cell(unknown_guards_positions, guard_seen_by)
                    if self.debug:
                        self.print_map()
                        self.print_map()
                        self.dimacs.print_cases_connues_map()
                    for pos in unknown_guards_positions:
                        result = self.dimacs.test_is_guard_in_cell(pos)
                        if result[0]:
                            guard_orientation: HC = self.get_offest_from_dir(self.position, result[1])
                            guard_type: HC = self.translation_dict[guard_orientation]
                            self.cases_connues[result[1]] = guard_type.value
                    if self.debug :
                        print(f"\tPOSITION : {self.position}")

    def add_case_connue_vision(self, vision: Dict[Tuple[int, int], int]):
        if self.phase == 1 and self.use_dimacs:
            self.dimacs.handle_vision(vision)
        for pos_case, value_case in vision:
            if pos_case in [3, 3]:
                print("ici")
            self.cases_connues[pos_case] = value_case.value

    def trun_to_direction(self, goal: Tuple[int, int]):
        rotation = self.obtenir_orientation(self.position, self.orientation, goal)
        if self.debug: print(rotation)
        nvlle_vision = None
        if rotation[0] == "TURN_CLOCKWISE":
            if self.debug: print("turn clock")
            nvlle_vision = self.referre.turn_clockwise()
            self.moves += 1
        elif rotation[0] == "TURN_ANTICLOCKWISE":
            if self.debug: print("turn anti")
            nvlle_vision = self.referre.turn_anti_clockwise()
            self.moves += 1
        elif rotation[0] == "DOUBLE_TURN_CLOCKWISE":
            if self.debug: print("double turn")
            nvlle_vision = self.referre.turn_clockwise()
            self.old_penalties = self.penalties
            self.add_case_connue_vision(vision=nvlle_vision["vision"])
            self.penalties = nvlle_vision["penalties"]
            nvlle_vision = self.referre.turn_clockwise()
            self.moves += 2
        else:
            if self.debug: print("MOVE NOT NEEDED!")
        if nvlle_vision is None:
            return [], rotation[1]
        self.add_case_connue_vision(vision=nvlle_vision["vision"])
        self.orientation = rotation[1]
        return

    def obtenir_orientation(self, current_position: Tuple[int, int], current_orientation: HC, goal: Tuple[int, int]) \
            -> Tuple[str, HC]:
        if current_position[1] == goal[1]:
            if current_position[0] > goal[0]:
                # Il faut aller à gauche
                if current_orientation == HC.N:
                    return "TURN_ANTICLOCKWISE", HC.W
                if current_orientation == HC.S:
                    return "TURN_CLOCKWISE", HC.W
                if current_orientation == HC.E:
                    return "DOUBLE_TURN_CLOCKWISE", HC.W
                return "MOVE_FORWARD", HC.W
            else:
                # Il faut aller à droite
                if current_orientation == HC.N:
                    return "TURN_CLOCKWISE", HC.E
                if current_orientation == HC.S:
                    return "TURN_ANTICLOCKWISE", HC.E
                if current_orientation == HC.W:
                    return "DOUBLE_TURN_CLOCKWISE", HC.E
                return "MOVE_FORWARD", HC.E
        else:
            if current_position[1] < goal[1]:
                # Il faut aller en haut
                if current_orientation == HC.S:
                    return "DOUBLE_TURN_CLOCKWISE", HC.N
                if current_orientation == HC.E:
                    return "TURN_ANTICLOCKWISE", HC.N
                if current_orientation == HC.W:
                    return "TURN_CLOCKWISE", HC.N
                return "MOVE_FORWARD", HC.N
            else:
                # Il faut aller en bas
                if current_orientation == HC.N:
                    return "DOUBLE_TURN_CLOCKWISE", HC.S
                if current_orientation == HC.E:
                    return "TURN_CLOCKWISE", HC.S
                if current_orientation == HC.W:
                    return "TURN_ANTICLOCKWISE", HC.S
                return "MOVE_FORWARD", HC.S

    def __get_offset(self, current_orientation: HC):
        if current_orientation == HC.N:
            offset = 0, 1
        elif current_orientation == HC.E:
            offset = 1, 0
        elif current_orientation == HC.S:
            offset = 0, -1
        elif current_orientation == HC.W:
            offset = -1, 0
        else:
            raise Exception("ORIENTATION_INCONNUE_DANS_VALUTATION")
        return offset

    def get_map_infos_for_referee(self, debug = False):
        map_info: Dict[Tuple[int, int], HC] = {}
        for i in range(self.total_y + 1):
            for j in range(self.total_x + 1):
                if (i, j) in self.cases_connues:
                    if debug: print(f"({i}, {j}) : {self.cases_connues[(i, j)]}")
                    if self.cases_connues[i, j] == -1:
                        map_info[(i, j)] = HC.EMPTY
                    else:
                        map_info[(i, j)] = HC(self.cases_connues[(i, j)])
        return map_info

    def get_move_needed(self, current_position: Tuple[int, int], current_orientation: HC, goal: Tuple[int, int]) -> \
            Tuple[
                int, HC]:
        orientation = self.obtenir_orientation(current_position, current_orientation, goal)
        if orientation[0] == "MOVE_FORWARD":
            return 1, orientation[1]
        elif orientation[0] == "TURN_CLOCKWISE" or orientation[0] == "TURN_ANTICLOCKWISE":
            return 2, orientation[1]
        else:
            return 3, orientation[1]

    def get_offset(self, current_orientation: HC):
        if current_orientation == HC.N:
            offset = 0, 1
        elif current_orientation == HC.E:
            offset = 1, 0
        elif current_orientation == HC.S:
            offset = 0, -1
        elif current_orientation == HC.W:
            offset = -1, 0
        else:
            raise Exception("ORIENTATION_INCONNUE_DANS_VALUTATION")
        return offset

    def get_offest_from_dir(self, current_position: Tuple[int, int], goal: Tuple[int, int]) -> HC:
        if current_position[0] < goal[0]:
            return HC.W
        elif current_position[0] > goal[0]:
            return HC.E
        elif current_position[1] < goal[1]:
            return HC.S
        elif current_position[1] > goal[1]:
            return HC.N
        else:
            raise Exception("POSITIONS_EGALE")

    def print_status(self, status):
        print("-------------------------------------------------------------------")
        for i in status:
            print("\t", i, " : ", status[i])
        print("-------------------------------------------------------------------")

    def print_map(self):
        print("-------------------------------------------------------------------")
        print(f"X := {self.total_x} / Y:= {self.total_y} \n")
        for i in range(self.total_y):
            x = self.total_y - i - 1
            ligne = f"{x} | "
            for j in range(self.total_x):
                y = j
                if (y, x) in self.cases_connues:
                    contenu = self.cases_connues[(y, x)]
                    if contenu == -1:
                        contenu = "     ?     "
                    else:
                        contenu = HC(contenu)
                    temp = f"{contenu}"
                    ligne += f"  {temp} {(13 - len(temp)) * ' '}|"
                else:
                    ligne += f"  INCONU {(y, x)} |"
            print(f"{ligne}")

        index = f"- | "
        for i in range(self.total_y + 1):
            index += f"{' ' * 7}{i}{' ' * 8}|"
        print(index)
        print("-------------------------------------------------------------------")
