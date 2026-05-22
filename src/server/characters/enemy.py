from math import atan2, sin, cos, sqrt
import time
import web_helper

IMG_SIZE = 64
MOVE_AMOUNT = 35

class Enemy:
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
        if time.time() - self.last_attack >= self.cooldown:
            player.hit(self.attack_amount)
            self.last_attack = time.time()
            
    def hit(self, damage: int):
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
        if self.within_range(player.get_center_pos()):
            self.attack(player)
        else:
            self.track_player(player.get_center_pos())
            self.x += self.move[0] * delta_time
            self.y += self.move[1] * delta_time
            self.helper.change_dimensions(self.id, (self.x, self.y))
