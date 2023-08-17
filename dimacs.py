import os
import shutil
import subprocess
from datetime import datetime
from itertools import combinations, product
from typing import Dict, Tuple, List, Optional
from sys import platform

from hitman.hitman import HC

PropositionnalVariable = int
Clause = List[PropositionnalVariable]
ClauseBase = List[Clause]

# Cell = Tuple[[int, int]
Map = Dict[Tuple[int, int], HC]


class Dimacs:
    def __init__(self, initial_status, debug=False):
        self.n_clause: int = 0
        self.n_var: int = 0
        self.clauses: ClauseBase = []

        self.total_x: int = initial_status["n"]
        self.total_y: int = initial_status["m"]

        self.n_guards: int = initial_status["guard_count"]
        self.n_civils: int = initial_status["civil_count"]
        self.knowns_cells: Dict[Tuple[int, int], bool] = {}
        self.n_total_entites = self.n_guards + self.n_civils
        self.known_guards: int = 0
        self.known_civils: int = 0

        self.nb_var = (self.total_x - 1) * self.total_x * 13 + self.total_y * 13 + 1
        self.debug = debug
        if debug: print(f"nb var : {self.nb_var}")

        self.cases_connues: Dict[Tuple[int, int], int] = {}
        self.exacly_known: Dict[Tuple[int, int], bool] = {}
        self.file_name = datetime.now().strftime("dimacs-%m_%d_%Y-%H:%M:%S.cnf")

        for i in range(self.total_x):
            for j in range(self.total_y):
                self.cases_connues[(i, j)] = None
                self.exacly_known[(i, j)] = False
                self.knowns_cells[(i, j)] = False

        self.to_explore = []
        self.add_init_constraints(initial_status)
        self.deducted_guards_cells = []

    def cell_to_variable(self, i: int, j: int, val: int) -> PropositionnalVariable:
        return i * self.total_x * 13 + j * 13 + val + 1

    def variable_to_cell(self, var: PropositionnalVariable) -> Tuple[int, int, int]:
        var -= 1
        val = var % 13
        var -= val
        j = (var // 13) % self.total_x
        var -= j * 13
        i = var // (self.total_x * 13)
        return i, j, val

    # au moins n variables vraies dans la liste
    def au_moins(self, n: int, vars: List[int]) -> List[Clause]:
        clauses = []
        for c in combinations(vars, len(vars) - (n - 1)):
            clauses.append(list(c))
        return clauses

    # au plus n variables vraies dans la liste
    def au_plus(self, n: int, vars: List[int]) -> List[Clause]:
        clauses = []
        for c in combinations([i * -1 for i in vars], n + 1):
            clauses.append(list(c))
        return clauses

    # exactement n variables vraies dans la liste
    def exactement(self, n: int, vars: List[int]) -> ClauseBase:
        if n == 0:
            return self.au_plus(0, vars)
        if n == len(vars):
            return self.au_moins(n, vars)
        if len(vars) == 0:
            return []
        clauses = self.au_plus(n, vars)
        clauses += self.au_moins(n, vars)
        return clauses

    def add_init_constraints(self, initial_status):
        clauses: ClauseBase = []
        clauses.append(
            [
                self.cell_to_variable(
                    initial_status["position"][0],
                    initial_status["position"][0],
                    HC.EMPTY.value,
                )
            ]
        )

        guards_var = []
        civils_var = []

        for i in range(self.total_x):
            for j in range(self.total_y):
                guards_var.append(
                    self.cell_to_variable(i, j, HC.GUARD_N.value)
                )
                civils_var.append(
                    self.cell_to_variable(i, j, HC.CIVIL_N.value)
                )

        clauses += self.exactement(self.n_guards, guards_var)
        clauses += self.exactement(self.n_civils, civils_var)

        piano_wire_constraints = self.create_piano_wire_constraints()
        suite_constraints = self.create_suit_constraints()
        cell_clauses = self.create_cells_constraints()
        target_constraints = self.create_target_constraints()
        # print(cell_clauses)
        clauses += (
                piano_wire_constraints
                + suite_constraints
                + cell_clauses
                + target_constraints
        )
        self.clauses += clauses
        self.dimacsToFile(filename=f"./cnf/{self.file_name}")

    def create_guard_constraints(self) -> Clause:
        clauses: Clause = []
        for i in range(self.total_x):
            for j in range(self.total_y):
                var = self.cell_to_variable(i, j, HC.GUARD.value)
                clauses.append(var)
        return clauses

    def create_civil_constraints(self) -> Clause:
        clauses: Clause = []
        for i in range(self.total_x):
            for j in range(self.total_y):
                var = self.cell_to_variable(i, j, HC.GUARD.value)
                clauses.append(var)
        return clauses

    def create_piano_wire_constraints(self) -> ClauseBase:
        vars: List[PropositionnalVariable] = []

        for i in range(self.total_x):
            for j in range(self.total_y):
                var = self.cell_to_variable(i, j, HC.PIANO_WIRE.value)
                vars.append(var)

        return self.exactement(1, vars)

    def create_suit_constraints(self) -> ClauseBase:
        vars: List[PropositionnalVariable] = []

        for i in range(self.total_x):
            for j in range(self.total_y):
                vars.append(self.cell_to_variable(i, j, HC.SUIT.value))

        return self.exactement(1, vars)

    def create_target_constraints(self) -> ClauseBase:
        vars: List[PropositionnalVariable] = []

        for i in range(self.total_x):
            for j in range(self.total_y):
                vars.append(self.cell_to_variable(i, j, HC.TARGET.value))

        return self.exactement(1, vars)

    def create_cells_constraints(self):
        clauses: ClauseBase = []
        for i in range(self.total_x):
            for j in range(self.total_y):
                cell_vars: List[PropositionnalVariable] = []
                possible_values = [HC.EMPTY.value, HC.WALL.value, HC.GUARD_N.value, HC.GUARD_E.value, HC.GUARD_S.value,
                                   HC.GUARD_W.value, HC.CIVIL_N.value, HC.CIVIL_E.value, HC.CIVIL_S.value,
                                   HC.CIVIL_W.value, HC.TARGET.value, HC.SUIT.value, HC.PIANO_WIRE.value, ]
                for val in possible_values:
                    cell_vars.append(self.cell_to_variable(i, j, val))
                clauses += self.exactement(1, cell_vars)
        return clauses

    def add_guard_in_cell(self, cell):
        guard_clause = self.cell_to_variable(cell[0], cell[1], HC.GUARD_N.value)
        self.add_clause_in_file([guard_clause])
        self.addClause([guard_clause])
        return

    def add_possible_guard_in_cell(self, cells, guard_number):
        vars = []
        for cell in cells:
            vars.append(self.cell_to_variable(cell[0], cell[1], HC.GUARD_N.value))
        exactement = self.exactement(guard_number, vars)
        self.clauses += exactement
        self.print_clauses(should_print=self.debug, clauses=exactement)

    def test_is_guard_in_cell(self, cell) -> Tuple[bool, Tuple[int, int]]:
        self.update_header_infos(self.file_name, None, len(self.clauses) + 1)
        if self.is_it_smart_to_test():
            guard_clause = -self.cell_to_variable(cell[0], cell[1], HC.GUARD_N.value)
            self.add_clause_in_file([guard_clause])
            solved = self.exec_gophersat(f"./cnf/{self.file_name}")
            if not solved:
                self.delete_last_line_in_file(self.file_name)
                self.add_clause_in_file([self.cell_to_variable(cell[0], cell[1], HC.GUARD_N.value)])
                return solved, cell
            self.delete_last_line_in_file(self.file_name)
        self.update_header_infos(self.file_name, None, len(self.clauses) - 1)
        return False, None

    def is_it_smart_to_test(self):
        return self.n_guards > self.known_guards

    def add_know_cells(self, cell, value):
        clauses_to_add = []
        possible_values = [
            HC.GUARD_N.value,
            HC.CIVIL_N.value,
            HC.TARGET.value, HC.PIANO_WIRE.value, HC.WALL.value, HC.EMPTY.value
        ]
        for values in possible_values:
            if values != value:
                clauses_to_add.append([-self.cell_to_variable(cell[0], cell[1], values)])

        return clauses_to_add

    def handle_noise(self, status):
        position = status["position"]
        noise = status["hear"]

        pos = []
        possible_offset = range(-2, 3)
        for i, j in product(possible_offset, repeat=2):
            pos_x, pos_y = position[0] + i, position[1] + j
            if self.total_x > pos_x >= 0 and self.total_y > pos_y >= 0:
                if (pos_x, pos_y) not in pos:
                    pos.append((pos_x, pos_y))

        if noise == 0:
            clauses_to_add = []
            for pos in pos:
                non_guard = -self.cell_to_variable(pos[0], pos[1], HC.CIVIL_N.value)
                non_civil = -self.cell_to_variable(pos[0], pos[1], HC.GUARD_N.value)
                self.cases_connues[pos] = -1
                clauses_to_add.append([non_guard])
                clauses_to_add.append([non_civil])
                self.clauses.append([non_guard])
                self.clauses.append([non_civil])
            self.add_clauses_in_file(clauses_to_add)
            if self.debug: self.print_cases_connues_map()
            return

        vars_to_add = []
        for pos in pos:
            vars_to_add.append(self.cell_to_variable(pos[0], pos[1], HC.CIVIL_N.value))
            vars_to_add.append(self.cell_to_variable(pos[0], pos[1], HC.GUARD_N.value))
        if self.debug: self.print_cases_connues_map()
        if noise < 5:
            exactement = self.exactement(noise, vars_to_add)
            for clause in exactement:
                self.clauses.append(clause)
            self.add_clauses_in_file(exactement)
            return
        else:
            au_moins_n_guard = self.au_moins(noise, vars_to_add)
            for clause in au_moins_n_guard:
                self.clauses.append(clause)
            self.add_clauses_in_file(au_moins_n_guard)
            return

    def handle_vision(self, vision):
        for coord, value in vision:
            if (
                    value == HC.GUARD_E
                    or value == HC.GUARD_N
                    or value == HC.GUARD_S
                    or value == HC.GUARD_W
            ):
                if coord in self.knowns_cells and not self.knowns_cells[coord]:
                    self.known_guards += 1
                    value = HC.GUARD_N
            elif (
                    value == HC.CIVIL_E
                    or value == HC.CIVIL_N
                    or value == HC.CIVIL_S
                    or value == HC.CIVIL_W
            ):
                if coord in self.knowns_cells and not self.knowns_cells[coord]:
                    self.known_guards += 1
                    value = HC.GUARD_N

            if coord in self.knowns_cells and not self.knowns_cells[coord]:
                self.knowns_cells[coord] = True
                clause = self.cell_to_variable(coord[0], coord[1], value.value)
                self.clauses.append([clause])
                self.add_clause_in_file([clause])
        return

    def old_test(self, cells):
        self.update_header_infos(self.file_name, None, len(self.clauses) + 1)
        for cell in cells:
            guard_var = -self.cell_to_variable(cell[0], cell[1], HC.GUARD_N.value)
            self.add_clause_in_file([guard_var])
            output = self.exec_gophersat(f"./cnf/{self.file_name}")
            if not output:
                cell = self.variable_to_cell(-guard_var)
                print(-guard_var)
                print(f"La cellule {(cell[0], cell[1])} contient un garde")
                return True, (cell[0], cell[1])
        self.update_header_infos(self.file_name, None, len(self.clauses) - 1)
        return False, None



    def test_is_cell_safe(self, cases_connues, noise, position, possible_guards_cells) -> Tuple[
        bool, Optional[Tuple[int, int]]]:
        if noise == 0:
            return False, None
        if not self.is_it_smart_to_test():
            return False, None

        pos = []
        possible_offset = range(-2, 3)
        for i, j in product(possible_offset, repeat=2):
            pos_x, pos_y = position[0] + i, position[1] + j
            if self.total_x > pos_x >= 0 and self.total_y > pos_y >= 0:
                if (pos_x, pos_y) not in pos:
                    pos.append((pos_x, pos_y))

        # on ajoute les clauses des cases connues
        unknown_noise = noise
        clauses: ClauseBase = []
        guards_value = [HC.GUARD_N.value, HC.GUARD_E.value, HC.GUARD_S.value, HC.GUARD_W.value, HC.CIVIL_N.value,
                        HC.CIVIL_E.value, HC.CIVIL_S.value, HC.CIVIL_W.value]
        for i, j in pos:
            if (i, j) in self.cases_connues and self.cases_connues[(i, j)] == -1:
                clauses.append([-self.cell_to_variable(i, j, HC.GUARD_N.value)])
                clauses.append([-self.cell_to_variable(i, j, HC.CIVIL_N.value)])
            val = cases_connues[(i, j)]
            if val != -1:
                if val in guards_value:
                    if val in [HC.CIVIL_N.value, HC.CIVIL_W.value, HC.CIVIL_E.value, HC.CIVIL_S.value]:
                        val = HC.CIVIL_N.value
                    if val in [HC.GUARD_N.value, HC.GUARD_W.value, HC.GUARD_E.value, HC.GUARD_S.value]:
                        val = HC.GUARD_N.value
                clauses.append([self.cell_to_variable(i, j, val)])
            # si garde ou civil
            if val in guards_value:
                unknown_noise -= 1 if noise < 5 else 0

        unknown_vars = []

        # on génére les uniques sur les cases de l'offset
        for i, j in pos:
            cell_vars: List[PropositionnalVariable] = []
            possible_values = [
                HC.EMPTY.value,
                HC.WALL.value,
                HC.GUARD_N.value,
                HC.CIVIL_N.value,
                HC.TARGET.value,
                HC.SUIT.value,
                HC.PIANO_WIRE.value,
            ]
            for val in possible_values:
                cell_vars.append(self.cell_to_variable(i, j, val))
            clauses += self.exactement(1, cell_vars)

            if cases_connues[(i, j)] == -1:
                unknown_vars.append(self.cell_to_variable(i, j, HC.CIVIL_N.value))
                unknown_vars.append(self.cell_to_variable(i, j, HC.GUARD_N.value))

        # on ajoute en fonction du noise
        if noise < 5:
            clauses += self.exactement(noise, unknown_vars)
        else:
            clauses += self.exactement(noise, unknown_vars)

        # pour savoir si la case est safe on teste si on sera dans la range d'un garde
        # on teste pas les cases connues
        possible_guards_vars = []

        for cell in possible_guards_cells:
            possible_guards_vars.append(
                self.cell_to_variable(cell[0], cell[1], HC.GUARD_N.value)
            )

        filename = (
            f"./cnf/tmp/{datetime.now().strftime('dimacs-%m_%d_%Y-%H:%M:%S.cnf')}"
        )
        self.dimacsToFile(filename=filename, clauses=clauses)

        for var_guard in possible_guards_vars:
            self.add_clause_in_file(
                [-var_guard],
            )
            output = self.exec_gophersat(filename)
            if not output:
                cell = self.variable_to_cell(var_guard)
                return True, (cell[0], cell[1])
        return False, None

    def print_clauses(self, clauses=None, should_print=False):
        if should_print:
            if clauses is None:
                clauses = self.clauses
            for clause in clauses:
                ligne = ""
                for c in clause:
                    if c < 0:
                        c = -c
                        ligne += "-"
                    ligne += str(self.variable_to_cell(c)) + " "
                print(ligne)

    def print_cases_connues_map(self):
        print("-------------------------------------------------------------------")
        print(f"X := {self.total_x} / Y:= {self.total_y} \n")
        for i in range(self.total_y):
            x = self.total_y - i - 1
            ligne = f"{x} | "
            for j in range(self.total_x):
                y = j
                if (y, x) in self.cases_connues:
                    contenu = self.cases_connues[(y, x)]
                    if contenu is None:
                        contenu = "X"
                    elif contenu == -1:
                        contenu = "N0"
                    ligne += f"      {contenu}{(10 - len(str(contenu))) * ' '}|"
                else:
                    ligne += f"   INCONU {(y, x)} |"
            print(f"{ligne}")
        print("-------------------------------------------------------------------")
        print(f"X := {self.total_x} / Y:= {self.total_y} \n")
        for i in range(self.total_y):
            x = self.total_y - i - 1
            ligne = f"{x} | "
            for j in range(self.total_x):
                y = j
                if (y, x) in self.exacly_known:
                    contenu = self.exacly_known[(y, x)]
                    if contenu is False:
                        contenu = "X"
                    else:
                        contenu = "E"
                    ligne += f"      {contenu}{(10 - len(str(contenu))) * ' '}|"
                else:
                    ligne += f"   INCONU {(y, x)} |"
            print(f"{ligne}")
        if self.debug:self.print_known_cells()

        index = f"- | "
        for i in range(self.total_y + 1):
            index += f"{' ' * 6}{i}{' ' * 7}|"
        print(index)
        print("-------------------------------------------------------------------")

    def print_known_cells(self):
        print("-------------------------------------------------------------------")
        print(f"X := {self.total_x} / Y:= {self.total_y} \n")
        for i in range(self.total_y):
            x = self.total_y - i - 1
            ligne = f"{x} | "
            for j in range(self.total_x):
                y = j
                if (y, x) in self.knowns_cells:
                    contenu = self.knowns_cells[(y, x)]
                    ligne += f"      {contenu}{(9 - len(str(contenu))) * ' '}|"
                else:
                    ligne += f"   INCONU {(y, x)} |"
            print(f"{ligne}")

        index = f"- | "
        for i in range(self.total_y + 1):
            index += f"{' ' * 6}{i}{' ' * 7}|"
        print(index)
        print("-------------------------------------------------------------------")

    def addClause(self, clause: Clause = None):
        if clause is not None:
            self.clauses.append(clause)

    def addClauses(self, clauses: ClauseBase):
        for c in clauses:
            self.addClause(c)

    def removeClause(self, clause: Clause):
        if clause in self.clauses:
            self.clauses.remove(clause)

    def removeClauses(self, clauses: ClauseBase):
        for clause in clauses:
            if clause in self.clauses:
                self.clauses.remove(clause)

    def update_header_infos(self, file_name: str = None, clauses: ClauseBase = None, length: int = None):
        if file_name is None:
            file_name = self.file_name
        if clauses is None:
            clauses = self.clauses
        f = open(f"./cnf/{file_name}", "r")
        lignes: List[str] = f.readlines()
        f.close()

        lignes[1] = f"p cnf {self.nb_var} {len(clauses) if length is None else length}\n"

        f = open(f"./cnf/{file_name}", "w", newline='\n')
        f.writelines(lignes)
        f.close()
        return

    def add_clause_in_file(self, clauses: Clause, file_name: str = None):
        if file_name is None:
            file_name = self.file_name
        texte: str = ""
        for var in clauses:
            texte += f"{str(var)} "
        texte += "0\n"

        f = open(f"./cnf/{file_name}", "a")
        f.write(texte)
        f.close()
        return

    def add_clauses_in_file(self, clauses: ClauseBase, file_name: str = None):
        if file_name is None:
            file_name = self.file_name
        texte: str = ""
        for var in clauses:
            for c in var:
                texte += f"{str(c)} "
        texte += "0\n"

        f = open(f"./cnf/{file_name}", "a")
        f.write(texte)
        f.close()
        return

    def delete_last_line_in_file(self, file_name: str = None):
        print("supprimer_clauses_in_file")
        if file_name is None:
            file_name = self.file_name
        f = open(f"./cnf/{file_name}", "r+")
        f.seek(0, os.SEEK_END)
        pos = f.tell() - 1
        # On remonte jusqu'au dernier caractere de la ligne
        while pos > 0 and f.read(1) != "\n":
            pos -= 1
            f.seek(pos, os.SEEK_SET)
        # On vérifie qu'on est en position positif pour pas déclencher d'erreur
        if pos > 0:
            f.seek(pos, os.SEEK_SET)
            f.truncate()
        return

    def create_file_copy(self) -> str:
        copy_name = datetime.now().strftime("dimacs-%m_%d_%Y-%H:%M:%S.cnf")
        shutil.copyfile(f"./cnf/{self.file_name}", f"./cnf/tests/{copy_name}")
        return copy_name

    def dimacsToString(self, clauses: ClauseBase = None) -> str:
        dimacsOut = "c Dimacs file for HITMAN \n"
        dimacsOut += "p cnf " + str(self.nb_var) + " " + str(len(clauses)) + "\n"
        for clause in clauses:
            for var in clause:
                dimacsOut += str(var) + " "
            dimacsOut += "0" + "\n"
        return dimacsOut

    def dimacsToFile(self, filename: str = None, clauses: ClauseBase = None):
        if clauses is None:
            clauses = self.clauses
        if filename is None:
            filename = self.file_name
        file = open(filename, "w")
        file.write(self.dimacsToString(clauses))
        file.close()

    def exec_gophersat(self, filename: str = None) -> bool:
        chemin_solver = "./solvers/gophersat/"
        if platform == "linux" or platform == "linux2" and chemin_solver == "":
            chemin_solver = "./solvers/gophersat/linux64/gophersat"
        elif platform == "darwin" and chemin_solver == "":
            chemin_solver = "./solvers/gophersat/macos64/gophersat"
        elif platform == "win32" and chemin_solver == "":
            chemin_solver = "./solvers/gophersat/win64/gophersat.exe"
        if chemin_solver == "./solvers/gophersat/":
            raise Exception(
                "Gophersat introuvable, SVP ajouter le chemin de votre gophersat dans le fichier 'dimacs.py' à la ligne 587, dans la variable chemin_solver !")
        if filename is None:
            raise Exception("Aucun fichier DIMACS n'a été spécifié !")
        try:
            result = subprocess.run(
                [chemin_solver, filename], capture_output=True, check=True, encoding='utf8'
            )
            string = str(result.stdout)
            lines = string.splitlines()
        except subprocess.CalledProcessError as e:
            raise RuntimeError("command '{}' return with error (code {}): {}".format(e.cmd, e.returncode, e.output))

        return True if lines[1] == "s SATISFIABLE" else False
