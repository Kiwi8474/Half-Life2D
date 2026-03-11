import pygame


class Entity:
    def __init__(self, x, y, width, height, color, sprite=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = color
        self.sprite = sprite
        self.vel_x = 0
        self.vel_y = 0
        self.gravity = 0.8
        self.on_ground = False
        self.facing_right = True

    def apply_gravity(self):
        self.vel_y += self.gravity
        if self.vel_y > 20:
            self.vel_y = 20

    def move(self, platforms):
        # Horizontal
        self.rect.x += self.vel_x
        for platform in platforms:
            if self.rect.colliderect(platform["rect"]):
                if self.vel_x > 0:
                    self.rect.right = platform["rect"].left
                if self.vel_x < 0:
                    self.rect.left = platform["rect"].right

        # Vertikal
        self.rect.y += self.vel_y
        self.on_ground = False

        for platform in platforms:
            if self.rect.colliderect(platform["rect"]):
                if self.vel_y > 0:  # fällt
                    self.rect.bottom = platform["rect"].top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:  # springt hoch
                    self.rect.top = platform["rect"].bottom
                    self.vel_y = 0

    def check_tile(self, layers):
        for layer in layers:
            for tile in layer:
                if self.rect.colliderect(tile["rect"]):
                    return tile["id"]
        return 0

    def update(self, all_objects):
        self.apply_gravity()
        self.move(all_objects["collision"])
        if self.vel_x > 0:
            self.facing_right = True
        elif self.vel_x < 0:
            self.facing_right = False

    def draw(self, screen, camera):
        if self.sprite:
            screen.blit(self.sprite, camera.apply(self.rect))
        else:
            pygame.draw.rect(screen, self.color, camera.apply(self.rect))
