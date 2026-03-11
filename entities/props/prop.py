from entities.entity import Entity


class Prop(Entity):
    def __init__(self, x, y, width, height, color="#BDBDBD", sprite=None, **kwargs):
        super().__init__(x, y, width, height, color, sprite)
        self.is_interactable = True
        self.gravity = 0
        for key, value in kwargs.items():
            setattr(self, key, value)

    def interact(self, player):
        pass

    def update(self, all_objects):
        if self.gravity > 0:
            super().update(all_objects)
