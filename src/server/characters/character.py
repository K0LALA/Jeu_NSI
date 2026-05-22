import web_helper

class Character:
    def __init__(self, helper: web_helper.Helper, name: str, position: tuple[int, int]):
        self.helper = helper
