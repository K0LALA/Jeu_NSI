from math import atan2, sin, cos
import time
import web_helper
from constants import PLAYER_SPRITESHEET_PATH, BASE_TILE_SIZE

from .weapon import Weapon
from .enemy import Enemy


ANIM_STOP           = PLAYER_SPRITESHEET_PATH + 'player_stop.gif'
ANIM_LEFT           = PLAYER_SPRITESHEET_PATH + 'player_left.gif'
ANIM_BOTTOM         = PLAYER_SPRITESHEET_PATH + 'player_bottom.gif'
ANIM_RIGHT          = PLAYER_SPRITESHEET_PATH + 'player_right.gif'
ANIM_TOP            = PLAYER_SPRITESHEET_PATH + 'player_top.gif'
ANIM_DEATH          = PLAYER_SPRITESHEET_PATH + 'player_death.gif'
ANIM_ATTACK_TOP     = PLAYER_SPRITESHEET_PATH + 'player_attack_top.gif'
ANIM_ATTACK_BOTTOM  = PLAYER_SPRITESHEET_PATH + 'player_attack_bottom.gif'
ANIM_ATTACK_RIGHT   = PLAYER_SPRITESHEET_PATH + 'player_attack_right.gif'
ANIM_ATTACK_LEFT    = PLAYER_SPRITESHEET_PATH + 'player_attack_left.gif'

IMG_SIZE = 64
MOVE_AMOUNT = 48
MIN_X = 0
MIN_Y = 0
ANIM_ATTACK_DURATION = 0.450    # 0.550
ANIM_DEATH_DURATION = 0.450     # Dans les faits cette valeur est égale à : 0.650
                                # Mais comme les updates ne se font pas toutes les nanosecondes, on pourrait dépasser ce temps et l'animation bouclerait, comme un glitch
                                # Pour éviter cela, on place la fin de l'animation au tout début de la dernière frame

# Contient le joueur
class Player:
    def __init__(self, helper: web_helper.Helper, map_center: tuple):
        self.helper = helper
        # X1, Y1, X2, Y2 pour l'image dans sa taille originale, il faut appliquer le zoom
        self.hitbox = (9, 19, 22, 23)
        self.width = IMG_SIZE
        self.height = IMG_SIZE
        # On place le joueur à l'origine, en appliquant la taille d'une tile et le zoom et en le centrant sur lui-même
        self.x = map_center[0] * BASE_TILE_SIZE * 2 - self.width / 2
        self.y = map_center[1] * BASE_TILE_SIZE * 2 - self.height / 2
        self.current_anim = ANIM_STOP
        w,h = self.helper.ws.get_window_size()
        self.id = self.helper.add_image(self.current_anim, ((w - self.width) / 2, (h - self.height) / 2), size=(self.width, self.height), parent="player")
        self.att = False
        self.delta_sum = 0
        
        self.health = 5
        self.max_health = 5
        for i in range(1,self.health+1):
            self.helper.ws.remove_class("heart" + str(i), "heart-hit")
        self.last_heal = time.time()
        self.dead = False

        self.weapon = Weapon(1, 40, 0.3)
        
        self.movement_vector = [0, 0]
        self.friction_coef = 0.8
        
    def update_graphics(self, window_size):
        self.helper.change_dimensions(self.id, position=((window_size[0] - self.width) / 2, (window_size[1] - self.height) / 2))
    
    def update(self, delta_time: float, keys: list, enemies: list[Enemy]) -> tuple[float, float]:
        if self.dead:
            if ANIM_DEATH_DURATION - self.delta_sum > 0.017: # Le temps d'une frame
                self.delta_sum += delta_time
            return [0,0]
        
        if 'KeyR' in keys:
            self.attack(enemies)
            self.att = True
            self.delta_sum = 0
            
        if ANIM_ATTACK_DURATION - self.delta_sum > 0.017:
            self.delta_sum += delta_time
        else:
            self.att = False

        if 'KeyH' in keys:
            self.heal(1)

        return self.update_movement(delta_time, keys) 
    
    def update_movement(self, delta_time: float, keys: list) -> tuple[float, float]:
        """
        delta_time est le temps en secondes depuis la derniere update, il sert de coefficient sur la vitesse de deplacement notamment
        """
        coef = delta_time * self.friction_coef
        self.movement_vector[0] *= coef
        self.movement_vector[1] *= coef
        self.movement_vector = [round(self.movement_vector[0], 3), round(self.movement_vector[1], 3)]
        movement_direction = self._process_move_keys(keys)
        new_anim = None
        if movement_direction != [0, 0]:
            angle = atan2(movement_direction[1], movement_direction[0])
            movement = (cos(angle) * MOVE_AMOUNT * delta_time * 2, sin(angle) * MOVE_AMOUNT * delta_time * 2)
            self.movement_vector[0] += movement[0]
            self.movement_vector[1] += movement[1]
            if abs(self.movement_vector[0]) > abs(self.movement_vector[1]):
                if self.movement_vector[0] > 0:
                    new_anim = ANIM_ATTACK_RIGHT if self.att else ANIM_RIGHT
                else:
                    new_anim = ANIM_ATTACK_LEFT if self.att else ANIM_LEFT
            else:
                if self.movement_vector[1] > 0 :
                    new_anim = ANIM_ATTACK_BOTTOM if self.att else ANIM_BOTTOM
                else:
                    new_anim = ANIM_ATTACK_TOP if self.att else ANIM_TOP
        else:
            new_anim = ANIM_ATTACK_BOTTOM if self.att else ANIM_STOP
        
        # On évite de changer trop les images, surtout pour les GIFs
        if new_anim != self.current_anim:
            self.current_anim = new_anim
            self.helper.change_image(self.id, self.current_anim, self.att)

        return self.movement_vector
        
    def _process_move_keys(self, keys: dict) -> list:
        """
        keys -- liste de touches appuyees, identifiees par leur code
        
        Renvoie un tuple definissant le mouvement selon le mouvement
        """
        move = [0, 0]
        if "KeyW" in keys:
            move[1] -= 1
        if "KeyA" in keys:
            move[0] -= 1
        if "KeyS" in keys:
            move[1] += 1
        if "KeyD" in keys:
            move[0] += 1
        return move
    
    def get_position(self):
        """
        Renvoie la position du joueur (x,y) sur la page par rapport a son coin superieur gauche
        """
        return (self.x, self.y)
    
    def get_boundaries(self, mov):
        """
        Renvoie le tuple (X1, Y1, X2, Y2) qui definit la boite de collisions du joueur, attention elle ne correspond pas exactement au visuel du joueur, elle est plus petite
        """
        return [self.get_position()[i%2] + mov[i%2] + self.hitbox[i] * 2 for i in range(4)]
    
    def get_center_pos(self):
        """
        Renvoie la position du joueur (x,y) sur la page centree sur le joueur
        """
        x = int(self.x + self.width / 2)
        y = int(self.y + self.height / 2)
        return (x,y)
        
    def render(self, movement_vector):
        """
        Actualise la position du joueur sur la page avec le mouvement stocké dans self.movement_vector
        """
        self.y += movement_vector[1]
        self.x += movement_vector[0]
        # Pas besoin, c'est la map qui le fait, on a cependant toujours besoin de savoir ou est le joueur
        #self.helper.change_dimensions(self.id, (self.x, self.y))
        
    def hit(self, damage: int):
        """
        Fait des degats au joueur
        
        Parametres:
            - damage: un entier donnant le nombre de PV que l'attaque doit infliger
        
        Renvoie True si le joueur est mort, False sinon
        """
        assert type(damage) == int, "Le nombre de dégats donné n'est pas entier"
        if not self.dead:
            self.helper.ws.add_tmp_class(self.id, "hit", 750)
            for i in range(min(5, damage)):
                self.helper.ws.add_class("heart"+str(self.health - i), "heart-hit")
            self.health = max(0, self.health - damage)
            if self.health == 0:
                self.dead = True
                self.delta_sum = 0
                self.helper.change_image(self.id, ANIM_DEATH, True)
        return self.dead
    
    def heal(self, cooldown: float):
        if time.time() - self.last_heal >= cooldown:
            self.health = min(self.health + 1, self.max_health)
            self.helper.ws.remove_class("heart" + str(self.health), "heart-hit")
            self.last_heal = time.time()

    def attack(self, enemies: list[Enemy]):
        self.weapon.attack(enemies)
        
    def is_dead(self):
        """
        Renvoie True si le joueur est mort, False sinon
        """
        return self.dead

        