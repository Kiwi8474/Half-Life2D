import pygame
from entities.enemies.enemy import Enemy
from spritesheet import SpriteSheet


class Headcrab(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, 32, 32, "#A58560", 30, 3)
        self.detection_range = 500
        self.jump_force = -10
        self.is_jumping = False
        self.last_jump_time = 0
        self.jump_cooldown = 1000
        self.damage = 10
        self.last_attack_time = 0
        self.attack_cooldown = 1000
        spritesheet = SpriteSheet("spritesheets/enemies.png")
        self.sprite_idle = spritesheet.get_image(0, 0, 48, 32)
        self.walk_sprites = [
            spritesheet.get_image(48, 0, 48, 32),
            spritesheet.get_image(0, 32, 48, 32),
        ]
        self.sprite_jump = spritesheet.get_image(96, 0, 32, 48)
        self.current_sprite = self.sprite_idle
        self.animation_index = 0
        self.animation_speed = 0.2
        self.animation_timer = 0

    def update(self, all_objects, player):
        current_time = pygame.time.get_ticks()

        dist_x = player.rect.centerx - self.rect.centerx
        dist_y = player.rect.centery - self.rect.centery
        distance = (dist_x**2 + dist_y**2) ** 0.5

        if distance < self.detection_range:
            if dist_x > 0:
                self.speed = abs(self.speed)
            else:
                self.speed = -abs(self.speed)

            if distance < 120 and self.on_ground and not self.is_jumping:
                self.vel_x = 0
                if current_time - self.last_jump_time > self.jump_cooldown:
                    jump_mod = 1.0
                    if player.crouching:
                        jump_mod = 0.6

                    self.vel_y = self.jump_force * jump_mod
                    self.vel_x = self.speed * 4
                    self.is_jumping = True
                    self.last_jump_time = current_time

            else:
                if not self.is_jumping:
                    self.vel_x = self.speed

        else:
            if not self.is_jumping:
                self.vel_x = 0

        self.apply_gravity()

        old_x = self.rect.x

        self.move(all_objects["collision"])

        if not self.is_jumping and self.on_ground and self.vel_x != 0:
            if abs(self.rect.x - old_x) < 1:
                self.vel_y = self.jump_force * 0.7
                self.vel_x = self.speed * 2
                self.is_jumping = True

        if self.vel_x > 0:
            self.facing_right = True
        elif self.vel_x < 0:
            self.facing_right = False

        if self.on_ground:
            self.is_jumping = False

        self.animate()

    def animate(self):
        if not self.on_ground:
            self.current_sprite = self.sprite_jump
        elif self.vel_x != 0:
            self.animation_timer += self.animation_speed
            if self.animation_timer >= len(self.walk_sprites):
                self.animation_timer = 0
            self.current_sprite = self.walk_sprites[int(self.animation_timer)]
        else:
            self.current_sprite = self.sprite_idle

    def draw(self, screen, camera):
        draw_sprite = self.current_sprite
        if not self.facing_right:
            draw_sprite = pygame.transform.flip(self.current_sprite, True, False)

        sprite_rect = draw_sprite.get_rect()
        sprite_rect.centerx = self.rect.centerx
        sprite_rect.bottom = self.rect.bottom

        screen.blit(draw_sprite, camera.apply(sprite_rect))
