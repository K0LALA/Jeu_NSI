from math import atan2, sin, cos, sqrt
import time
import web_helper

from .character import Character
from .weapon import Weapon

IMG_SIZE = 64
MOVE_AMOUNT = 35

class Enemy(Character):
    def track_player(self, player_position: tuple[int], delta_time: float):
        center_position = self.get_center_position()
        dX = player_position[0] - center_position[0]
        dY = player_position[1] - center_position[1]
        angle = atan2(dY, dX)
        self.movement_vector = [cos(angle) * self.speed * delta_time, sin(angle) * self.speed * delta_time]

    def within_range(self, player_position: tuple[int]):
        center_position = self.get_center_position()
        distance_squared = (player_position[0] - center_position[0]) ** 2
        distance_squared += (player_position[1] - center_position[1]) ** 2
        return distance_squared <= self.weapon.range ** 2
    
    def update(self, delta_time: float, player):
        if self.within_range(player.get_center_position()):
            self.attack([player])
            self.movement_vector = [0, 0]
        else:
            self.track_player(player.get_center_position(), delta_time)
        return self.movement_vector

class Enemy_OLD:
    def __init__(self, web_helper: web_helper.Helper, position: tuple, img_path: str, health: int):
        self.helper = web_helper
        
        self.x = position[0] - IMG_SIZE / 2
        self.y = position[1] - IMG_SIZE / 2
        
        self.id = self.helper.add_image(img_path, (self.x, self.y), size=(IMG_SIZE, IMG_SIZE), parent="tiles")
        
        # TODO: Ajouter de la regen
        self.health = health
        self.dead = False
        self.range = 32
        self.last_attack = time.time()
        self.cooldown = 1.3
        self.attack_amount = 1
        self.weapon = Weapon(self, 1, 32, 1.3)
        
        self.movement = (0, 0)
        
    def get_center_pos(self):
        return (self.x + IMG_SIZE / 2, self.y + IMG_SIZE / 2)
        
    def track_player(self, player_position: tuple):
        """
        Cette methode permet de faire aller l'ennemi dans la direion du joueur
        """
        # On calcule l'angle de deplacement
        X = player_position[0]
        Y = player_position[1]
        c_pos = self.get_center_pos()
        dX = X - c_pos[0]
        dY = Y - c_pos[1]
        a = atan2(dY, dX)
        # On ajuste le mouvement de l'ennemi pour aller vers le joueur
        self.move = (cos(a) * MOVE_AMOUNT, sin(a) * MOVE_AMOUNT)
        
    def within_range(self, position: tuple):
        c_pos = self.get_center_pos()
        distance = (position[0] - c_pos[0]) ** 2
        distance += (position[1] - c_pos[1]) ** 2
        distance = sqrt(distance)
        return distance <= self.range
        
    def attack(self, player):
        self.weapon.attack([player])
            
    def hit(self, damage: int, _=None):
        if not self.dead:
            self.helper.ws.add_tmp_class(self.id, "hit", 750)
            self.health -= damage
            self.health = max(0, self.health)
            if self.health == 0:
                self.helper.remove_html(self.id)
                self.dead = True
            
    def is_dead(self):
        return self.dead

    def update(self, delta_time: float, player):
        if self.within_range(player.get_center_position()):
            self.attack(player)
        else:
            self.track_player(player.get_center_position())
            self.x += self.move[0] * delta_time
            self.y += self.move[1] * delta_time
            self.helper.change_dimensions(self.id, (self.x, self.y))
