import pygame
from entities.entity import Entity


class Enemy(Entity):
    def __init__(self, x, y, width, height, color, health, speed):
        super().__init__(x, y, width, height, color)
        self.health = health
        self.speed = speed
        self.vel_x = self.speed
        self.damage = 10
        self.is_dead = False

    def update(self, all_objects, player):
        self.vel_x = self.speed

        super().update(all_objects)

        if self.vel_x == 0:
            self.speed *= -1

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.is_dead = True
