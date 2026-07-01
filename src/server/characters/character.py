import sqlite3
import web_helper
from constants import CHARACTERS_PATH

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
    # Une liste des animations disponibles (valeur) pour chaque spritesheet (clé)
    AVAILABLE_ANIMATIONS: dict[str, dict[str, None]] = dict()
    
    def init_spritesheets(ws):
        """
        Cette fonction envoie au JS toutes les informations sur les spritesheets depuis la BD
        
        Elle charge également Character.AVAILABLE_ANIMATIONS, qui pour chaque spritesheet, donne une liste des animations possibles
        
        Les animations sont pour la plupart de la forme `NOM_ANIMATION;DIRECTION` mais certaine comme `die` ne le sont pas
        """
        link = sqlite3.connect(CHARACTERS_PATH)
        base = link.cursor()
        
        # name, path, size
        base.execute("SELECT * FROM spritesheet;")
        
        spritesheets = base.fetchall()
        for spritesheet in spritesheets:
            name,path,size = spritesheet
            Character.AVAILABLE_ANIMATIONS[name] = dict()
            animation_map: dict[str, int] = dict()
            base.execute("SELECT * FROM animations WHERE spritesheet_id=?;", (name,))
            animations = base.fetchall()
            animation: list[str]
            for animation in animations:
                animation_name,_,position,repeat,count,durations = animation
                Character.AVAILABLE_ANIMATIONS[name][animation_name] = None
                durations_list = list(map(int, durations.split(',')))
                animation_map[animation_name] = [position,repeat,count,durations_list]
            ws.injecte(f"addAnimation('{name}','{path}',{size},{animation_map});")
    
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
        self.action = "idle"
        self.direction = ""
        
        self.dead = False

        self.fetch_attributes()
        
        self.initialize()
    
    def fetch_attributes(self):
        link = sqlite3.connect(CHARACTERS_PATH)
        base = link.cursor()
        
        base.execute("SELECT * FROM character WHERE name=?;", (self.name,))
        
        attributes_list = base.fetchall()
        if len(attributes_list) != 1:
            raise ValueError("Le personnage n'est pas unique ou n'existe pas dans la base de données")
        
        
        # name, w, h, hx1, hy1, hx2, hy2, spritesheet, health, weapon, speed
        attributes = attributes_list[0]
        if len(attributes) != 11:
            raise ValueError("Le nombre d'attributs n'est pas le bon, 11 sont attendus.")
        
        if attributes[1] != attributes[2]: raise ValueError("La taille du personnage ne représente pas un carré")
        
        self.size = attributes[1]
        self.hitbox = (attributes[3], attributes[4], attributes[5], attributes[6])
        
        self.spritesheet = attributes[7]
        
        base.execute("SELECT size FROM spritesheet WHERE name=?;", (self.spritesheet,))
        
        results = base.fetchall()
        if len(results) != 1:
            raise ValueError("La base de donnees ne contient pas la spritesheet ou plusieurs portent le meme nom.")
        
        self.scale = self.size / results[0][0]
        
        self.health = self.MAX_HEALTH = attributes[8]
        
        base.execute("SELECT damage, range, cooldown FROM weapon WHERE weapon_id=?;", (attributes[9],))
        
        weapon_attributes_list = base.fetchall()
        if len(weapon_attributes_list) != 1:
            raise ValueError("L'arme n'est pas unique ou n'existe pas dans la base de données")
        
        weapon_attributes = weapon_attributes_list[0]
        self.weapon = Weapon(self, weapon_attributes[0], weapon_attributes[1], weapon_attributes[2])
        
        self.speed = attributes[10]
        
        link.close()
    
    def initialize(self):
        self.helper.ws._push([{"id":"canvas-characters","type":"add_ch","data":{"name":self.name,"animation":self.spritesheet,"start_anim":self.action+';'+self.direction,"x":self.x,"y":self.y,"size":self.size}}])
    
    def remove(self):
        self.helper.ws._push([{"id":"canvas-characters","type":"remove_ch","data":{"name":self.name}}])
    
    def has_animation(self, animation):
        return animation in Character.AVAILABLE_ANIMATIONS[self.spritesheet]
    
    def change_animation_if_exists(self, new_action, new_direction=None):
        """
        Change l'animation en cours pour celle en paramètre
        
        Si la nouvelle animation est la même que l'ancienne, aucun changement n'est fait
        """       
        if new_direction == None:
            new_direction = self.direction
         
        if new_action == self.action and new_direction == self.direction:
            return
        
        new_animation = new_action + ";"
        new_animation += new_direction
            
        if self.has_animation(new_animation):
            self.action = new_action
            self.direction = new_direction
            self.render()
        
    def render(self):
        """
        Change l'animation côté client
        """
        # Si le personnage est mort, on ne change pas son animation
        if self.dead:
            return
        self.helper.ws._push([{"id":"canvas-characters","type":"change_ch","data":{"name":self.name,"animation":(self.action+";"+self.direction)}}])

    def update_render(self):
        """
        Cette méthode actualise le rendu du personnage si nécessaire par rapport à self.movement_vector
        """
        new_action = self.action
        new_direction = self.direction
        if self.movement_vector == [0, 0]:
            new_action = "idle"
        elif abs(self.movement_vector[0]) > abs(self.movement_vector[1]):
            new_action = "walk"
            if self.movement_vector[0] >= 0:
                new_direction = "right"
            else:
                new_direction = "left"
        else:
            new_action = "walk"
            if self.movement_vector[1] >= 0 :
                new_direction = "front"
            else:
                new_direction = "back"
        
        self.change_animation_if_exists(new_action, new_direction)
            
    def attack(self, targets):
        """
        Attaque chacune des cibles données par le paramètre targets
        
        L'attaque est gérée par Weapon, qui gère notamment le cooldown
        """
        self.change_animation_if_exists("attack")
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
            if self.name == "player":
                for i in range(min(5, damage)):
                    self.helper.ws.add_class("heart"+str(self.health - i), "heart-hit")
            self.health = max(0, self.health - damage)
            if self.health == 0:
                self.change_animation_if_exists("die", "")
                self.dead = True
            else:
                self.change_animation_if_exists("hurt")
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
        b = [self.get_position()[i%2] + self.hitbox[i] * self.scale for i in range(4)]
        return b

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
        