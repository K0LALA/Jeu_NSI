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
    def __init__(self, helper: web_helper.Helper, name: str, position: tuple[int, int], spritesheet: str):
        self.helper = helper
        self.name = name
        self.x, self.y = position
        
        self.movement_vector = [0, 0]
        self.direction = FRONT
        self.action = IDLE
        
        self.helper.ws.injecte(f"add_character('{name}', '{spritesheet}', {self.x}, {self.y}, 64);")
        
    def render(self):
        """
        Change l'animation côté client
        """
        self.helper.ws.injecte(f"change_render('{self.name}',{min(12, self.direction+self.action)},{self.x},{self.y});")
        
    def update_render(self):
        """
        Cette méthode actualise le rendu du personnage si nécessaire par rapport à self.movement_vector
        """
        render = False
        if abs(self.movement_vector[0]) > abs(self.movement_vector[1]):
            if self.movement_vector[0] > 0:
                if self.direction != RIGHT:
                    render = True
                self.direction = RIGHT
            else:
                if self.direction != LEFT:
                    render = True
                self.direction = LEFT
        else:
            if self.movement_vector[1] > 0 :
                if self.direction != FRONT:
                    render = True
                self.direction = FRONT
            else:
                if self.direction != BACK:
                    render = True
                self.direction = BACK
        
        if render:
            self.render()
    