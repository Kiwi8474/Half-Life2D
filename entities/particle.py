import random
from entities.entity import Entity


class Particle(Entity):
    def __init__(
        self, x, y, size, color, life_min=40, life_max=80, can_collide=True, sprite=None
    ):
        size = random.uniform(size - 2, size + 4)
        super().__init__(x, y, size, size, color, sprite)

        self.vel_x = random.uniform(-4, 4)
        self.vel_y = random.uniform(-7, -2)

        self.life = random.randint(life_min, life_max)
        self.gravity = 0.5

        self.can_collide = can_collide

    def update(self, all_objects):
        if self.can_collide:
            super().update(all_objects)
        else:
            self.vel_y += self.gravity
            self.rect.x += self.vel_x
            self.rect.y += self.vel_y
        self.life -= 1
        if self.on_ground:
            self.vel_x *= 0.8
