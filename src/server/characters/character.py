import web_helper

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
    def __init__(self, player, helper: web_helper.Helper, name: str, position: tuple[int, int], spritesheet: str, size: int):
        self.player = player
        self.helper = helper
        self.name = name
        # Position logique utilisée notamment pour les collisions
        self.x, self.y = position
        self.size = size
        # Position du personnage sur la carte, elle dépend de celle du joueur
        self.map_x = self.map_y = 0
        
        self.movement_vector = [0, 0]
        self.direction = FRONT
        self.action = IDLE
        
        self.dead = False
        
        self.helper.ws.injecte(f"add_character('{name}', '{spritesheet}', {self.map_x}, {self.map_y}, {self.size});")
        
    def calc_map_position(self):
        """
        Calcule la position du personnage sur la carte, elle dépend de cele du joueur et de la taille de la fenêtre
        """
        assert self.player != None, "self.player n'est pas initialisé"
        w, h = self.helper.ws.get_window_size()
        # On récupère la position du joueur
        self.map_x = (w - self.size) / 2 + (self.player.x) - self.x
        self.map_y = (h - self.size) / 2 + (self.player.y) - self.y
    
    def render(self):
        """
        Change l'animation côté client
        """
        # Si le joueur est mort, on ne change pas son animation
        if self.dead:
            return
        # On veut pas faire ça pour le joueur, celle-ci est déjà calculée dans le constructeur du joueur
        if self.name != "player":
            self.calc_map_position()
        self.helper.ws.injecte(f"change_render('{self.name}',{min(12, self.direction+self.action)},{self.map_x},{self.map_y});")
        
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
            
    def attack(self):
        self.action = ATTACK
        self.render()
        
    def hit(self, damage: int):
        self.helper.ws.injecte(f"hit_character('{self.name}');")
        
    def __del__(self):
        self.helper.ws.injecte(f"remove_character('{self.name}');")
    