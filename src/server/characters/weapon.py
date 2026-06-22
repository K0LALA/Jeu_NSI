import time

class Weapon:
    def __init__(self, source, damage: int, range: int, cooldown: float):
        self.source = source
        self.damage = damage
        self.range = range
        self.cooldown = cooldown

        self.last_attack = time.time()
    
    def attack(self, targets):
        if time.time() - self.last_attack >= self.cooldown:
            for target in targets:
                target.hit(self.damage, self.source)
            self.last_attack = time.time()