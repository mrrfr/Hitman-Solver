Prédicats fluents:
 - Hitman(x,y)
 - RegardeNord()
 - RegardeOuest()
 - RegardeEst()
 - RegardeSud()
 - Costume(x,y)
 - CordePiano(x,y) 
 - PossederCostume()
 - PossederCordePiano()

Prédicats fixes:
 - Mur(x,y)
 - Garde(x,y)
 - Civil(x,y)
 - Cible(x,y)
 - Case(x,y)
 

Actions:
 - PrendreCostume(x,y)
 Prec: Costume(x,y) et Hitman(x,y)
 Res:  -Costume(x,y)

[//]: #
- MettreCostume(x,y)
Prec: PossederCostume()
Res: -PossederCostume()

[//]: # 
 - PrendreCordePiano(x,y)
 Prec: CordePiano(x,y) et Hitman(x,y)
 Res: -CordiePiano(x,y) et PossederCordePiano()

[//]: # 

 - TuerCible(x,y)
 Prec: Cible(x,y) et PossederCordePiano()
 Res: -Cible(x,y)

 [//]: # (Pour neutraliser un garde il faut être tourner vers regarder vers sa position et qu"il ne nous regarde pas, faut check notre orientation et son orientation)


 - NeutraliserGardeCivilOuest(x,y)
 Prec: -Hitman(x-1,y) et ( Hitman(x+1,y) et RegardeOuest() ou Hitman(x, y-1) et RegardeNord() ou Hitman(x, y+1) et RegardeSud() ) et ( Garde(x,y) ou Civil(x,y) )
 Res: -Garde(x,y) et -Civil(x,y)

[//]: #
 - NeutraliserGardeCivilEst(x,y)
 Prec: -Hitman(x+1,y) et ( Hitman(x-1,y) et RegardeEst() ou Hitman(x, y-1) et RegardeNord() ou Hitman(x, y+1) et RegardeSud() ) et ( Garde(x,y) ou Civil(x,y) )
 Res: -Garde(x,y) et -Civil(x,y)

[//]: #
 - NeutraliserGardeCivilNord(x,y)
 Prec: -Hitman(x,y+1) et ( Hitman(x,y-1) et RegardeNord() ou Hitman(x, y-1) et RegardeNord() ou Hitman(x, y+1) et RegardeSud() ) et ( Garde(x,y) ou Civil(x,y) )
 Res: -Garde(x,y) et -Civil(x,y)

[//]: #
 - NeutraliserGardeCivilSud(x,y)
 Prec: -Hitman(x,y-1) et ( Hitman(x,y+1) et RegardeNord() ou Hitman(x, y-1) et RegardeNord() ou Hitman(x, y+1) et RegardeSud() ) et ( Garde(x,y) ou Civil(x,y) )
 Res: -Garde(x,y) et -Civil(x,y)

[//]: #

 - AvancerHaut(x,y)
 Prec: RegardeNord() et -Mur(x,y+1) et -Garde(x,y+1) et Case(x,y+1)
 Res: Hitman(x, y+1)

[//]: #
 - AvancerBas(x,y)
 Prec: RegardeSud() et -Mur(x,y-1) et -Garde(x,y-1) et Case(x,y-1)
 Res: Hitman(x, y-1)

[//]: #
- AvancerGauche()
 Prec: RegardeOuest() et -Mur(x-1,y) et -Garde(x-1,y) et Case(x-1,y)
 Res: Hitman(x-1, y)

[//]: #
 - AvancerDroite()
 Prec: RegardeEst() et -Mur(x+1,y) et -Garde(x+1,y) et Case(x+1,y)
 Res: Hitman(x+1, y)

[//]: #
- RegarderNord()
Prec: RegardeOuest() ou RegardeEst()
Res: RegardeNord()

[//]: #
- RegarderSud()
Prec: RegardeOuest() ou RegardeEst()
Res: RegardeSud()

[//]: #
- RegarderOuest()
Prec: RegardeNord() ou RegardeSud()
Res: RegardeOuest()

[//]: #
- RegarderEst()
Prec: RegardeNord() ou RegardeSud()
Res: RegardeEst()