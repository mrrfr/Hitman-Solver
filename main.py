import sys

from joueur import Joueur


def print_help():
    print("Usage: python3 main.py [SAT|NO-SAT] [args]")
    print("Options:")
    print("\tNO-SAT : Désactive l'utilisation du solver SAT")
    print("\tSAT : Active l'utilisation du solver SAT")
    print("Args:")
    print("\t--h : affiche ce help")
    print("\t--debug : Active le mode debug, par défaut le mode est désactivé")


def main(args):
    if len(args) == 0:
        print_help()
    else:
        sat_found = False
        sat = False
        for arg in args:
            if arg.lower().strip() in ["sat", "no-sat"]:
                if sat_found:
                    print("Vous ne pouvez pas spécifier deux fois si vous voulez utiliser le solver SAT ou non")
                    print_help()
                    return
                if arg.lower().strip() == "sat":
                    sat = True
                sat_found = True
            if arg.lower().strip() not in ["no-sat", "sat", "--debug", "--h"]:
                print("Argument inconnu : " + arg)
                print_help()
                return

        if not sat_found:
            print("Vous devez spécifier si vous voulez utiliser le solver SAT ou non")
            print_help()
            return

        debug = False
        if "--debug" in args:
            debug = True
    print(f"Récapitulatif des choix : ")
    print("\t Utilisation du solver SAT : " + str(sat))
    print("\t Mode debug : " + str(debug))
    joueur = Joueur(debug=debug, with_sat=sat)
    joueur.play_phase_1()
    joueur.print_res(joueur.phase_1_res)
    joueur.play_phase_2()


if __name__ == '__main__':
    main(sys.argv[1:])
