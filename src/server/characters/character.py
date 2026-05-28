import web_helper

class Character:
    def __init__(self, helper: web_helper.Helper, name: str, position: tuple[int, int], spritesheet: str):
        self.helper = helper
        self.name = name
        self.x, self.y = position
        self.helper.ws.injecte(f"characterMap.set('{name}', new Character('{name}', '{spritesheet}', {self.x}, {self.y}, 64));")
        
    def render(self):
        """
        Change l'animation côté client
        """
        self.helper.ws.injecte(f"update_render({self.name},{self.current_anim},{self.x},{self.y});")
    