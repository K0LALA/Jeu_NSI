from characters.npc import Interactable
import web_helper

IMAGE_PATH = "assets/tilesets/x16_decorations/x16_decorations_085.png"

class Waypoint(Interactable):
    def __init__(self, helper: web_helper.Helper, position: tuple, destination: str, distance: int = 30):
        self.helper = helper
        self.position = position
        self.x = self.position[0]
        self.y = self.position[1]
        self.distance = distance
        self.destination = destination
        self.width = self.height = 32
        
        self.opened = False
        self.tp = False

        self.id = self.helper.add_image(IMAGE_PATH, self.position, size=(self.width, self.height), parent='tiles')

    def interact(self):
        """
        appelee quand on appuie sur la touche d'interaction
        """
        self.opened = True
        self.helper.change_text("action-bar", str(self.destination))

    def is_opened(self):
        return self.opened
    
    def key(self, key: str):
        if key == "Enter":
            self.opened = False
            self.helper.change_text("action-bar", "")
            self.tp = True
            return
        elif key == "Backspace":
            self.opened = False
            self.helper.change_text("action-bar", "")
            return
