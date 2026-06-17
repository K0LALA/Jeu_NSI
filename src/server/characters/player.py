from math import atan2, sin, cos
import time
import web_helper
from constants import BASE_TILE_SIZE

from .character import Character, DIE
from .enemy import Enemy

IMG_SIZE = 64
MOVE_AMOUNT = 48

# Contient le joueur
class Player(Character):
    def __init__(self, helper: web_helper.Helper, map_center: tuple):
        
        position = (map_center[0] * BASE_TILE_SIZE * 2 - IMG_SIZE / 2, \
                    map_center[1] * BASE_TILE_SIZE * 2 - IMG_SIZE / 2)
        
        super().__init__(None, helper, "player", position)

        # Ces coordonnées ne changent que lorsque la page change dans self.update_graphics
        w,h = self.helper.ws.get_window_size()
        self.map_x = (w - self.size) / 2
        self.map_y = (h - self.size) / 2
        self.render()
        
        for i in range(1,self.health+1):
            self.helper.ws.remove_class("heart" + str(i), "heart-hit")
        self.last_heal = time.time()
        
        self.friction_coef = 0.8
        
    def update_graphics(self, window_size):
        self.map_x = (window_size[0] - self.size) / 2
        self.map_y = (window_size[1] - self.size) / 2
        self.render()
    
    def update(self, delta_time: float, keys: list, enemies: list[Enemy]) -> tuple[float, float]:
        if self.dead:
            return [0,0]
        
        if 'KeyR' in keys:
            self.attack(enemies)

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
        if movement_direction != [0, 0]:
            angle = atan2(movement_direction[1], movement_direction[0])
            movement = (cos(angle) * MOVE_AMOUNT * delta_time * 2, sin(angle) * MOVE_AMOUNT * delta_time * 2)
            self.movement_vector[0] += movement[0]
            self.movement_vector[1] += movement[1]
        
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
    
    def heal(self, cooldown: float):
        if time.time() - self.last_heal >= cooldown:
            self.health = min(self.health + 1, self.MAX_HEALTH)
            self.helper.ws.remove_class("heart" + str(self.health), "heart-hit")
            self.last_heal = time.time()
        