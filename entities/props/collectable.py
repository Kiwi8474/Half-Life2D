from entities.props.prop import Prop


class Collectable(Prop):
    def __init__(self, x, y, width, height, color="#BDBDBD", sprite=None, **kwargs):
        super().__init__(x, y, width, height, color, sprite, **kwargs)
        self.gravity = 0.8

    def interact(self, player):
        player.inventory.append(self.name)
