import pygame
import random
import math
from entities.entity import Entity
from entities.particle import Particle
from entities.enemies.enemy import Enemy
from entities.enemies.headcrab import Headcrab
from spritesheet import SpriteSheet


class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 20, 64, "#f08800")
        self.speed = 5
        self.jump_force = -18.5
        self.crouching = False
        self.normal_height = 64
        self.crouch_height = 32
        self.health = 100
        self.shield = 0
        self.last_damage_time = 0
        self.damage_cooldown = 250
        self.facing_right = True
        self.in_acid = False
        self.in_spikes = False
        self.weapon_selected = 0
        self.inventory = []
        self.shoot_cooldown = 0
        self.last_shot_tick = 0
        self.mouse_was_pressed = False
        self.walk_animation_index = 0
        self.walk_animation_speed = 0.12
        player_spritesheet = SpriteSheet("spritesheets/gordon.png")
        weapons_spritesheet = SpriteSheet("spritesheets/weapons.png")
        self.player_sprites = {
            "idle": player_spritesheet.get_image(0, 0, 50, 72),
            "crouching": player_spritesheet.get_image(0, 0, 50, 42),
        }
        self.walk_sprites = [
            player_spritesheet.get_image(50, 0, 50, 72),
            player_spritesheet.get_image(100, 0, 50, 72),
            player_spritesheet.get_image(150, 0, 50, 72),
            player_spritesheet.get_image(200, 0, 50, 72),
        ]
        self.weapon_sprites = {
            "Crowbar": weapons_spritesheet.get_image(0, 0, 10, 32),
            "Glock": weapons_spritesheet.get_image(10, 0, 20, 16),
        }

    def handle_input(self, keys, platforms, enemies, particle_list):
        self.vel_x = 0

        if self.health <= 0:
            return

        weapon_keys = {
            pygame.K_1: 0,
            pygame.K_2: 1,
            pygame.K_3: 2,
            pygame.K_4: 3,
            pygame.K_5: 4,
            pygame.K_6: 5,
            pygame.K_7: 6,
            pygame.K_8: 7,
            pygame.K_9: 8,
            pygame.K_0: 9,
        }

        for key, weapon_index in weapon_keys.items():
            if keys[key] and weapon_index < len(self.inventory):
                self.weapon_selected = weapon_index
                break

        mouse_buttons = pygame.mouse.get_pressed()
        mouse_down = mouse_buttons[0]

        if len(self.inventory) > 0:
            if self.inventory[self.weapon_selected] == "Glock":
                if mouse_down and not self.mouse_was_pressed:
                    self.shooting(platforms, enemies, particle_list)
            else:
                if mouse_down:
                    self.shooting(platforms, enemies, particle_list)

        self.mouse_was_pressed = mouse_down

        if keys[pygame.K_a]:
            self.vel_x = -self.speed
            self.facing_right = False
        if keys[pygame.K_d]:
            self.vel_x = self.speed
            self.facing_right = True

        if keys[pygame.K_SPACE] and self.on_ground:
            self.vel_y = self.jump_force
            self.on_ground = False

        if keys[pygame.K_c]:
            if not self.crouching:
                if self.on_ground:
                    self.rect.y += self.normal_height - self.crouch_height
                self.rect.height = self.crouch_height
                self.crouching = True
        else:
            if self.crouching:
                temp_rect = pygame.Rect(
                    self.rect.x,
                    self.rect.y - (self.normal_height - self.crouch_height),
                    self.rect.width,
                    self.normal_height,
                )

                # Prüfen ob Platz zum aufstehen
                can_stand_up = True
                for platform in platforms:
                    if temp_rect.colliderect(platform["rect"]):
                        can_stand_up = False
                        break

                if can_stand_up:
                    # Vergrößern
                    self.rect.height = self.normal_height
                    self.rect.y -= self.normal_height - self.crouch_height
                    self.crouching = False

    def handle_damage(self, amount):
        if self.health <= 0:
            return

        current_time = pygame.time.get_ticks()
        if current_time - self.last_damage_time > self.damage_cooldown:
            if self.shield <= 0:
                self.health -= amount
            else:
                self.shield -= amount // 2

            if self.shield < 0:
                self.shield = 0

            self.last_damage_time = current_time

    def spawn_hit_particles(self, x, y, target, particle_list):
        p_color = "#CCCCCC"

        speed_factor = 2

        if isinstance(target, Headcrab):
            p_color = "#B9B965"
        elif isinstance(target, Enemy):
            p_color = "#FF0000"
        elif target == "wall":
            p_color = "#FFD900"
            speed_factor = 10

        for _ in range(8):
            if target == "wall":
                p = Particle(x, y, 4, p_color, 3, 5, False)
            else:
                p = Particle(x, y, 4, p_color)

            winkel = random.uniform(-math.pi / 4, math.pi / 4)
            kraft = random.uniform(2, 6)
            p.vel_x = math.cos(winkel) * kraft * (1 if self.facing_right else -1)
            p.vel_y = math.sin(winkel) * kraft
            if target == "wall":
                p.gravity = 0

            particle_list.append(p)

    def shooting(self, platforms, enemies, particle_list):
        if not self.inventory:
            return

        current_weapon = self.inventory[self.weapon_selected]

        if current_weapon == "Crowbar":
            if self.shoot_cooldown > 0:
                return

            attack_width = 64
            attack_height = 64
            attack_x = (
                self.rect.right if self.facing_right else self.rect.left - attack_width
            )
            attack_y = self.rect.centery - attack_height // 2

            attack_rect = pygame.Rect(attack_x, attack_y, attack_width, attack_height)

            for enemy in enemies:
                if attack_rect.colliderect(enemy.rect):
                    enemy.take_damage(10)
                    self.spawn_hit_particles(
                        enemy.rect.centerx, enemy.rect.centery, enemy, particle_list
                    )
                    break

            self.shoot_cooldown = 20
            return

        if current_weapon == "Glock":
            if self.shoot_cooldown > 0:
                return

            self.last_shot_tick = pygame.time.get_ticks()

            hand_y_offset = 22
            if self.crouching:
                hand_y_offset = 10

            hand_y = self.rect.y + self.rect.height // 2 - hand_y_offset

            start_x = self.rect.centerx
            start_y = hand_y
            end_x = start_x + (1000 if self.facing_right else -1000)

            ray_rect = pygame.Rect(start_x, start_y, abs(end_x - start_x), 2)
            if not self.facing_right:
                ray_rect.x = end_x

            target_hit = None
            min_dist = 10000

            for enemy in enemies:
                if ray_rect.colliderect(enemy.rect):
                    dist = abs(self.rect.centerx - enemy.rect.centerx)
                    if dist < min_dist:
                        min_dist = dist
                        target_hit = enemy

            for wall in platforms:
                if ray_rect.colliderect(wall["rect"]):
                    dist = abs(self.rect.centerx - wall["rect"].centerx)
                    if dist < min_dist:
                        min_dist = dist
                        target_hit = "wall"

            if isinstance(target_hit, Enemy):
                target_hit.take_damage(15)

            hit_dist = min_dist if target_hit else 1000
            shot_end_x = start_x + (hit_dist if self.facing_right else -hit_dist)

            if target_hit:
                self.spawn_hit_particles(shot_end_x, start_y, target_hit, particle_list)

            self.shoot_cooldown = 10
            return

    def check_loading_zone(self, active_props):
        for prop in active_props:
            if getattr(prop, "is_loading_zone", False):
                if self.rect.colliderect(prop.rect):
                    return True
        return False

    def update(self, keys, all_objects, enemies, particle_list):
        if self.health > 0:
            if self.shoot_cooldown > 0:
                self.shoot_cooldown -= 1

            self.handle_input(keys, all_objects["collision"], enemies, particle_list)

            if self.vel_x != 0:
                test_rect = self.rect.copy()
                test_rect.x += self.vel_x

                for wall in all_objects["collision"]:
                    if test_rect.colliderect(wall["rect"]):
                        step_up_rect = test_rect.copy()
                        step_up_rect.y -= 16

                        can_step_up = True
                        for check_wall in all_objects["collision"]:
                            if step_up_rect.colliderect(check_wall["rect"]):
                                can_step_up = False
                                break

                        if can_step_up and self.on_ground:
                            self.rect.y -= 16
                        break

            if self.vel_x != 0 and self.on_ground and not self.crouching:
                self.walk_animation_index += self.walk_animation_speed
                if self.walk_animation_index >= len(self.walk_sprites):
                    self.walk_animation_index = 0
            else:
                self.walk_animation_index = 0

            tile_id = self.check_tile(
                (all_objects["collision"], all_objects["foreground"])
            )
            self.in_acid = tile_id == 20

            self.gravity = 1.0
            self.speed = 5.0

            if tile_id == 20:  # Säure
                self.handle_damage(4)
                self.gravity = 0.5

                if self.vel_y > 2:
                    self.vel_y = 2

                self.in_acid = True

            elif tile_id == 21:  # Spikes
                self.handle_damage(6)

            for enemy in enemies:
                if self.rect.colliderect(enemy.rect):
                    self.handle_damage(enemy.damage)

            if self.crouching:
                self.speed -= 2.5

            if self.in_acid:
                self.speed -= 1.5

        super().update(all_objects)

    def draw(self, screen, camera):
        if self.crouching:
            current_sprite = self.player_sprites["crouching"]
        elif self.vel_x != 0 and self.on_ground and not self.crouching:
            current_sprite = self.walk_sprites[int(self.walk_animation_index)]
        else:
            current_sprite = self.player_sprites["idle"]

        if not self.facing_right:
            current_sprite = pygame.transform.flip(current_sprite, True, False)

        sprite_rect = current_sprite.get_rect()
        sprite_rect.centerx = self.rect.centerx
        sprite_rect.bottom = self.rect.bottom

        screen.blit(current_sprite, camera.apply(sprite_rect))

        if self.inventory and self.weapon_selected < len(self.inventory):
            current_weapon_name = self.inventory[self.weapon_selected]
            weapon_sprite = self.weapon_sprites.get(current_weapon_name)

            if weapon_sprite:
                if not self.facing_right:
                    weapon_sprite = pygame.transform.flip(weapon_sprite, True, False)

                hand_y_offset = 10 if self.crouching else 22
                hand_y = self.rect.y + self.rect.height // 2 - hand_y_offset

                w_rect = weapon_sprite.get_rect()

                if self.facing_right:
                    w_rect.left = self.rect.right
                else:
                    w_rect.right = self.rect.left

                w_rect.centery = hand_y
                screen.blit(weapon_sprite, camera.apply(w_rect))

            flash_duration = 50
            if pygame.time.get_ticks() - self.last_shot_tick < flash_duration:
                flash_color = (255, 255, 100)
                flash_x = w_rect.right if self.facing_right else w_rect.left
                flash_pos = camera.apply_pos((flash_x, hand_y))
                pygame.draw.circle(screen, flash_color, flash_pos, 6)
