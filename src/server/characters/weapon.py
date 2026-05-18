import time

class Weapon:
    def __init__(self, damage: int, range: int, cooldown: float, durability: int=-1):
        self.damage = damage
        self.range = range
        self.cooldown = cooldown
        self.weapon = ['bow','crossbow','sword']
        # Not used as of right now
        self.durability = durability

        self.last_attack = time.time()
    
    def attack(self, targets):
        if time.time() - self.last_attack >= self.cooldown:
            for target in targets:
                target.hit(self.damage)
            self.last_attack = time.time()

    def change_weapon(self):
        pass

