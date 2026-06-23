import sqlite3
import web_helper
from constants import CHARACTERS_PATH, ZOOM

from .weapon import Weapon

# Direction
FRONT       = 0
RIGHT       = 1
BACK        = 2
LEFT        = 3

# Action
IDLE        = 0
WALK        = 4
ATTACK      = 8
DIE         = 12

class Character:
    def __init__(self, player, helper: web_helper.Helper, name: str, position: tuple[int, int]):
        """
        Initialise un personnage, cette classe est abstraite, elle n'est pas censée être utilisée directement pour créer un personnage
        
        Les attributs de base sont initialisés, comme le nom du personnage, la vie, la position logique et graphique ou le mouvement du personnage
        
        Certains attributs sont récupérés de la base de données, comme la spritesheet, la vie, l'arme et la hitbox
        
        Paramètres:
            - player: L'instance du joueur, elle est utilisée pour déterminer la position du personnage sur l'écran, car elle dépend de celle du joueur
            
            - helper: Une instance de Helper, pour pouvoir modifier des éléments sur la page avec WsInter
            
            - name: Une chaine de caractères dont la taille est comprise entre 1 et 20 inclus. Permet de récupérer les attributs du personnage dans la base de données `characters.db`
            
            - position: Un tuple d'entiers qui donne la position logique du personnage
        """
        if not 1 <= len(name) <= 20:
            raise ValueError("La taille du nom du personnage doit etre comprise entre 1 et 20 inclus")
        
        self.player = player # Utilisé par les personnages autre que le joueur pour déterminer leur position sur l'écran
        self.helper = helper
        self.name = name
        # Position logique utilisée notamment pour les collisions
        self.x, self.y = position
        
        self.movement_vector = [0, 0]
        self.direction = FRONT
        self.action = IDLE
        
        self.dead = False

        self.fetch_attributes()
        
        self.initialize(self.animation)
    
    def fetch_attributes(self):
        link = sqlite3.connect(CHARACTERS_PATH)
        base = link.cursor()
        
        base.execute("SELECT * FROM character WHERE name=?;", (self.name,))
        
        attributes_list = base.fetchall()
        if len(attributes_list) != 1:
            raise ValueError("Le personnage n'est pas unique ou n'existe pas dans la base de données")
        
        
        # name, w, h, hx1, hy1, hx2, hy2, tileset, health, weapon, speed
        attributes = attributes_list[0]
        if len(attributes) != 11:
            raise ValueError("Le nombre d'attributs n'est pas le bon, 11 sont attendus.")
        
        if attributes[1] != attributes[2]: raise ValueError("La taille du personnage ne représente pas un carré")
        
        self.size = attributes[1]
        self.hitbox = (attributes[3], attributes[4], attributes[5], attributes[6])
        
        self.animation = attributes[7]
        
        self.health = self.MAX_HEALTH = attributes[8]
        
        base.execute("SELECT damage, range, cooldown FROM weapon WHERE weapon_id=?;", (attributes[9],))
        
        weapon_attributes_list = base.fetchall()
        if len(weapon_attributes_list) != 1:
            raise ValueError("L'arme n'est pas unique ou n'existe pas dans la base de données")
        
        weapon_attributes = weapon_attributes_list[0]
        self.weapon = Weapon(self, weapon_attributes[0], weapon_attributes[1], weapon_attributes[2])
        
        self.speed = attributes[10]
        
        link.close()
    
    def initialize(self, animation):
        self.helper.ws._push([{"id":"canvas-characters","type":"add_ch","data":{"name":self.name,"animation":animation,"x":self.x,"y":self.y,"size":self.size}}])
    
    def remove(self):
        self.helper.ws._push([{"id":"canvas-characters","type":"remove_ch","data":{"name":self.name}}])
    
    def render(self):
        """
        Change l'animation côté client
        """
        # Si le personnage est mort, on ne change pas son animation
        if self.dead:
            return
        self.helper.ws._push([{"id":"canvas-characters","type":"change_ch","data":{"name":self.name,"animation":min(12, self.direction+self.action)}}])

    def update_render(self):
        """
        Cette méthode actualise le rendu du personnage si nécessaire par rapport à self.movement_vector
        """
        new_action = self.action
        new_direction = self.direction
        if self.movement_vector == [0, 0]:
            new_action = IDLE
        elif abs(self.movement_vector[0]) > abs(self.movement_vector[1]):
            new_action = WALK
            if self.movement_vector[0] >= 0:
                new_direction = RIGHT
            else:
                new_direction = LEFT
        else:
            new_action = WALK
            if self.movement_vector[1] >= 0 :
                new_direction = FRONT
            else:
                new_direction = BACK
        
        if new_action != self.action or new_direction != self.direction:
            self.action = new_action
            self.direction = new_direction
            self.render()
            
    def attack(self, targets):
        """
        Attaque chacune des cibles données par le paramètre targets
        
        L'attaque est gérée par Weapon, qui gère notamment le cooldown
        """
        self.action = ATTACK
        self.render()
        self.weapon.attack(targets)
        
    def hit(self, damage: int, source = None):
        """
        Fait des dégâts au personnage
        
        Paramètres:
            - damage: Un entier donnant le nombre de dégâts à infliger au personnage
            
            - source: Une instance de Character à l'initiative de l'attaque
            
        Renvoie True si le personnage est mort, False sinon
        """
        if type(damage) != int or damage < 0:
            raise ValueError("damage doit etre un entier positif")
        if not self.dead:
            self.helper.ws._push([{"id":"canvas-characters","type":"hit_ch","data":{"name":self.name}}])
            #self.helper.ws.injecte(f"hit_character('{self.name}');")
            if self.name == "player":
                for i in range(min(5, damage)):
                    self.helper.ws.add_class("heart"+str(self.health - i), "heart-hit")
            self.health = max(0, self.health - damage)
            if self.health == 0:
                self.action = DIE
                self.render()
                self.dead = True
        return self.dead
    
    def is_dead(self):
        """
        Renvoie True si le joueur est mort, False sinon
        """
        return self.dead
    
    def get_position(self):
        """
        Renvoie la position logique du personnage sous la forme d'un tuple (x, y) sur la page par rapport à son coin supérieur gauche
        """
        return (self.x, self.y)
    
    def get_boundaries(self):
        """
        Renvoie le tuple (X1, Y1, X2, Y2) qui définit la boîte de collisions du personnage.
        
        On y applique le zoom définit en constante dans libs.constants
        
        Elle ne correspond donc pas au visuel du joueur
        """
        return [self.get_position()[i%2] + self.hitbox[i] * ZOOM for i in range(4)]
    
    def get_center_position(self):
        """
        Renvoie la position du centre du personnage sous la forme (x, y)
        """
        x = self.x + self.size / 2
        y = self.y + self.size / 2
        return (x, y)
    
    def validate_position(self, movement_vector):
        """
        Actualise la position logique et graphique du personnage
        
        Cette méthode est utilisée lorsque CollisionResolver a validé le mouvement, le personnage peut alors bouger
        
        On utilise le vecteur passé en paramètre pour modifier la position du personage
        """
        self.x += movement_vector[0]
        self.y += movement_vector[1]
        if movement_vector != [0, 0]:
            self.helper.ws._push([{"id":"canvas-characters","type":"move_ch","data":{"name":self.name,"x":self.x,"y":self.y}}])
        self.update_render()
        