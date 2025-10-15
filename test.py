import wsinter
from time import sleep

from random import randint

test=wsinter.Inter()

test.demarre(page="page.html",clavier=True)

y = 100
x = 100

# déplacer l'image au clavier
def hbgd(s,d):
    global x,y
    if s=="D":
        if d[5]=='KeyW':
            y-=2
        elif d[5]=='KeyS':
            y+=2
        elif d[5]=='KeyA':
            x-=2
        elif d[5]=='KeyD':
            x+=2

    test.attributs('img01',style={"left":str(x)+"px","top":str(y)+"px"})

# faire sauter l'image quand on clic dessus
def jump(s,d):
    global x,y
    if s=="D":
        if d[0]=='img01':
            x=randint(0,800)
            y=randint(0,800)
            test.attributs('img01',style={"left":str(x)+"px","top":str(y)+"px"})

def animer():
    global x
    while x < 800:
        sleep(0.05)
        x+=1
        test.attributs('img01',style={"left":str(x)+"px"})
        

# ajouter l'image dynamiquement
test.insere("img01","img",attr={'src':'sprite.png'},style={"position":"absolute","left":str(x)+"px","top":str(y)+"px"})

# définir les événements clavier et souris
test.gestionnaire_clavier(hbgd)
test.gestionnaire_souris(jump)
