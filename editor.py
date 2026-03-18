import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
import json
import pygame
import tkinter as tk
from tkinter import filedialog
from camera import Camera
from spritesheet import SpriteSheet
from registry import entity_types, prop_types

COLLECTABLES = ["Crowbar", "Glock"]
PROPS = ["HealStation", "ShieldStation"]
ENEMIES = ["Headcrab"]
LAYERS = ["deco", "collision", "foreground"]

CHUNK_W, CHUNK_H = 1280, 720
TILE_SIZE = 16

master_layout_img = None
chunk_cache = {}


def init():
    pygame.init()
    screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
    pygame.display.set_caption("Half-Life: 2D Editor")
    pygame.display.set_icon(pygame.image.load("img/game.ico"))
    return screen, pygame.Surface((1280, 720))


def load_assets():
    ps = SpriteSheet("spritesheets/props.png")
    ws = SpriteSheet("spritesheets/weapons.png")
    return {
        "HealStation": ps.get_image(0, 0, 40, 56),
        "ShieldStation": ps.get_image(40, 0, 40, 56),
        "Crowbar": ws.get_image(0, 0, 10, 32),
        "Glock": ws.get_image(10, 0, 20, 16),
    }


def load_master(path):
    if path and os.path.exists(path):
        return pygame.image.load(path).convert()
    return None


def get_data_from_master(master_img, chunk_x, chunk_y):
    try:
        chunk_surf = master_img.subsurface(
            pygame.Rect(chunk_x * 80, chunk_y * 45, 80, 45)
        )
    except ValueError:
        return None

    generated = {"deco": [], "collision": [], "foreground": []}

    for y in range(45):
        for x in range(80):
            pixel = chunk_surf.get_at((x, y))
            real_x = (chunk_x * CHUNK_W) + (x * TILE_SIZE)
            real_y = (chunk_y * CHUNK_H) + (y * TILE_SIZE)
            rect = pygame.Rect(real_x, real_y, TILE_SIZE, TILE_SIZE)

            if pixel.r > 0:
                generated["collision"].append({"rect": rect, "id": pixel.r})
            if pixel.g > 0:
                generated["deco"].append({"rect": rect, "id": pixel.g})
            if pixel.b > 0:
                generated["foreground"].append({"rect": rect, "id": pixel.b})
    return generated


def get_active_chunks(cam_x, cam_y, chapter_data, active_enemies, active_props, assets):
    global master_layout_img, chunk_cache

    if master_layout_img is None:
        master_layout_img = load_master(chapter_data.get("layout"))

    cx, cy = int(cam_x // CHUNK_W), int(cam_y // CHUNK_H)
    res = {"deco": [], "collision": [], "foreground": []}

    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            cur_x, cur_y = cx + dx, cy + dy
            key = f"{cur_x},{cur_y}"

            if key not in chunk_cache:
                if master_layout_img:
                    gen = get_data_from_master(master_layout_img, cur_x, cur_y)
                    if gen:
                        chunk_cache[key] = gen

            cached = chunk_cache.get(key)
            if cached:
                for l in ["deco", "collision", "foreground"]:
                    res[l].extend(cached[l])

            c_info = chapter_data["chunks"].get(key)
            if c_info:
                for e in c_info.get("enemies", []):
                    cl = entity_types.get(e["type"])
                    if cl:
                        active_enemies.append(
                            cl(cur_x * CHUNK_W + e["x"], cur_y * CHUNK_H + e["y"])
                        )
                for p in c_info.get("props", []):
                    cl = prop_types.get(p["type"])
                    if cl:
                        active_props.append(
                            cl(
                                cur_x * CHUNK_W + p["x"],
                                cur_y * CHUNK_H + p["y"],
                                p.get("width", 32),
                                p.get("height", 32),
                                assets=assets,
                                name=p.get("name"),
                            )
                        )
    return res


def mainloop(screen, window):
    cam_x, cam_y = 640, 360
    camera = Camera(1280, 720)
    clock = pygame.time.Clock()

    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        initialdir="chapters", filetypes=[("JSON", "*.json")]
    )
    if not path:
        return

    data = json.load(open(path))
    assets = load_assets()
    ts = SpriteSheet("spritesheets/tilesheet.png")

    texs = {
        i: ts.get_image(x, y, 16, 16)
        for i, (x, y) in {
            0: (112, 112),
            255: (0, 0),
            245: (16, 0),
            235: (32, 0),
            225: (48, 0),
            215: (64, 0),
            205: (80, 0),
            195: (96, 0),
            185: (112, 0),
            175: (0, 16),
            165: (16, 16),
            155: (32, 16),
        }.items()
    }

    items = ENEMIES + PROPS + COLLECTABLES
    sel_idx = 0
    running = True

    while running:
        clock.tick(60)
        keys = pygame.key.get_pressed()
        spd = 15 if not keys[pygame.K_LSHIFT] else 30

        if keys[pygame.K_a]:
            cam_x -= spd
        if keys[pygame.K_d]:
            cam_x += spd
        if keys[pygame.K_w]:
            cam_y -= spd
        if keys[pygame.K_s]:
            cam_y += spd
        camera.camera.topleft = (-cam_x + 640, -cam_y + 360)

        mx, my = pygame.mouse.get_pos()
        ww, wh = window.get_size()
        rx, ry = mx * 1280 // ww, my * 720 // wh
        gx, gy = ((rx - camera.camera.x) // 16) * 16, (
            (ry - camera.camera.y) // 16
        ) * 16

        ckey = f"{int(gx // CHUNK_W)},{int(gy // CHUNK_H)}"
        lx, ly = int(gx % CHUNK_W), int(gy % CHUNK_H)

        enemies, props = [], []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s and (
                    keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]
                ):
                    json.dump(data, open(path, "w"), indent=4)
                if event.key == pygame.K_r:
                    global master_layout_img
                    master_layout_img = None
                    chunk_cache.clear()

            if event.type == pygame.MOUSEWHEEL:
                sel_idx = (sel_idx + event.y) % len(items)
            if event.type == pygame.MOUSEBUTTONDOWN:
                if ckey not in data["chunks"]:
                    data["chunks"][ckey] = {"enemies": [], "props": []}
                if event.button == 1:
                    item = items[sel_idx]
                    if item in ENEMIES:
                        data["chunks"][ckey].setdefault("enemies", []).append(
                            {"type": item, "x": lx, "y": ly}
                        )
                    elif item in PROPS:
                        data["chunks"][ckey].setdefault("props", []).append(
                            {"type": item, "x": lx, "y": ly, "width": 32, "height": 32}
                        )
                    elif item in COLLECTABLES:
                        data["chunks"][ckey].setdefault("props", []).append(
                            {
                                "type": "Collectable",
                                "name": item,
                                "x": lx,
                                "y": ly,
                                "width": 32,
                                "height": 32,
                            }
                        )
                if event.button == 3:
                    chunk = data["chunks"][ckey]
                    chunk["enemies"] = [
                        e
                        for e in chunk.get("enemies", [])
                        if not (e["x"] == lx and e["y"] == ly)
                    ]
                    chunk["props"] = [
                        p
                        for p in chunk.get("props", [])
                        if not (p["x"] == lx and p["y"] == ly)
                    ]

        objs = get_active_chunks(cam_x - 640, cam_y - 360, data, enemies, props, assets)
        screen.fill("#1a1a1a")

        for l in ["deco", "collision"]:
            for t in objs[l]:
                screen.blit(texs.get(t["id"], texs[0]), camera.apply(t["rect"]))

        for p in props:
            p.draw(screen, camera)
        for e in enemies:
            e.draw(screen, camera)
        for t in objs["foreground"]:
            screen.blit(texs.get(t["id"], texs[0]), camera.apply(t["rect"]))

        pygame.draw.rect(
            screen, "#FFD900", camera.apply(pygame.Rect(gx, gy, 16, 16)), 2
        )
        info = [
            f"ITEM: {items[sel_idx]}",
            f"CHUNK: {ckey}",
            "CTRL+S: Save | R: Reload Master",
        ]
        for i, t in enumerate(info):
            screen.blit(
                pygame.font.SysFont("Arial", 20, True).render(t, True, "#FFD900"),
                (10, 10 + i * 25),
            )

        pygame.transform.scale(screen, window.get_size(), window)
        pygame.display.flip()


if __name__ == "__main__":
    win, s = init()
    mainloop(s, win)
