from math import atan2, sin, cos
import time
import web_helper
from constants import BASE_TILE_SIZE, ZOOM

from .character import Character, FRONT, IDLE
from .enemy import Enemy

# Contient le joueur
class Player(Character):
    def __init__(self, helper: web_helper.Helper, map_center: tuple):        
        self.helper = helper
        self.name = "player"
        
        self.fetch_attributes()
        
        self.x = map_center[0] * BASE_TILE_SIZE * ZOOM - self.size / 2
        self.y = map_center[1] * BASE_TILE_SIZE * ZOOM - self.size / 2
        
        self.direction = FRONT
        self.action = IDLE
        self.movement_vector = [0,0]
        self.friction_coef = 0.8
        
        self.dead = False

        self.initialize()
        
        for i in range(1,self.health+1):
            self.helper.ws.remove_class("heart" + str(i), "heart-hit")
        self.last_heal = time.time()
        
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
            movement = (cos(angle) * self.speed * delta_time * ZOOM, sin(angle) * self.speed * delta_time * ZOOM)
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
        