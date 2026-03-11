import pygame
from entities.props.prop import Prop


class HealStation(Prop):
    def __init__(self, x, y, width, height, color="#BDBDBD", sprite=None, **kwargs):
        super().__init__(x, y, width, height, color, sprite, **kwargs)
        self.charges = 50
        self.heal_speed = 2
        all_assets = kwargs.get("assets")
        if all_assets:
            self.full_asset = all_assets.get("HealStation")
            self.empty_asset = all_assets.get("EmptyHealStation")
            self.sprite = self.full_asset
        self.last_heal_time = 0
        self.heal_cooldown = 250

    def update(self, all_objects):
        super().update(all_objects)
        if self.charges <= 0:
            self.sprite = self.empty_asset

    def interact(self, player):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_heal_time > self.heal_cooldown:
            if self.charges > 0 and player.health < 100:
                player.health += self.heal_speed
                self.charges -= self.heal_speed

                self.last_heal_time = current_time

                if player.health > 100:
                    player.health = 100
