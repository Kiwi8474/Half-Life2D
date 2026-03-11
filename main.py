import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
import json
import pygame
import ctypes
import math
from entities.entity import Entity
from entities.particle import Particle
from entities.player import Player
from entities.enemies.headcrab import Headcrab
from entities.props.collectable import Collectable
from camera import Camera
from spritesheet import SpriteSheet
from registry import entity_types, prop_types

chunk_cache = {}
initialized_chunks = {}
world_state = {}

master_layout_img = None
current_layout_path = None
master_lightmap_img = None
current_lightmap_path = None


def init():
    pygame.init()
    screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE | pygame.SCALED)
    pygame.display.set_caption("Half-Life: 2D")
    pygame.display.set_icon(pygame.image.load("img/game.ico"))
    display_surface = pygame.Surface((1280, 720))
    return screen, display_surface


def load_prop_assets():
    spritesheet = SpriteSheet("spritesheets/props.png")
    return {
        "HealStation": spritesheet.get_image(0, 0, 40, 56),
        "ShieldStation": spritesheet.get_image(40, 0, 40, 56),
        "EmptyHealStation": spritesheet.get_image(0, 56, 40, 56),
        "EmptyShieldStation": spritesheet.get_image(40, 56, 40, 56),
    }


def load_weapon_assets():
    spritesheet = SpriteSheet("spritesheets/weapons.png")
    return {
        "Crowbar": spritesheet.get_image(0, 0, 10, 32),
        "Glock": spritesheet.get_image(10, 0, 20, 16),
    }


def load_chapter(filename):
    with open(filename) as f:
        return json.load(f)


def save_game(player, current_chapter, world_state, filename):
    serializable_world_state = {}

    for chapter, data in world_state.items():
        serializable_world_state[chapter] = {
            "dead_enemies": list(data.get("dead_enemies", [])),
            "used_props": data["used_props"],
            "collected_items": list(data.get("collected_items", [])),
        }

    save_data = {
        "player": {
            "health": player.health,
            "shield": player.shield,
            "inventory": player.inventory,
            "weapon_selected": player.weapon_selected,
            "x": player.rect.x,
            "y": player.rect.y,
        },
        "current_chapter": current_chapter,
        "world_state": serializable_world_state,
    }

    with open(filename, "w") as f:
        json.dump(save_data, f, indent=4)


def load_game(filename):
    if not os.path.exists(filename):
        return None

    with open(filename, "r") as f:
        save_data = json.load(f)

    loaded_world_state = {}
    for chapter, data in save_data["world_state"].items():
        loaded_world_state[chapter] = {
            "dead_enemies": set(data.get("dead_enemies", [])),
            "used_props": data["used_props"],
            "collected_items": set(data.get("collected_items", [])),
        }

    save_data["world_state"] = loaded_world_state
    return save_data


def load_master(image_path):
    if not os.path.exists(image_path):
        return None
    return pygame.image.load(image_path).convert_alpha()


def get_data_from_master(master_img, chunk_x, chunk_y, tile_size):
    try:
        chunk_surf = master_img.subsurface(
            pygame.Rect(chunk_x * 80, chunk_y * 45, 80, 45)
        )
    except ValueError:
        return None

    generated = {"deco": [], "collision": [], "foreground": [], "lightmap": None}

    for y in range(45):
        for x in range(80):
            pixel = chunk_surf.get_at((x, y))

            real_x = (chunk_x * 1280) + (x * tile_size)
            real_y = (chunk_y * 720) + (y * tile_size)
            rect = pygame.Rect(real_x, real_y, tile_size, tile_size)

            # R-Kanal: Collision Tiles
            if pixel.r > 0:
                generated["collision"].append({"rect": rect, "id": pixel.r})

            # G-Kanal: Deko Tiles (Hintergrund)
            if pixel.g > 0:
                generated["deco"].append({"rect": rect, "id": pixel.g})

            # B-Kanal: Foreground Tiles (vor dem Spieler)
            if pixel.b > 0:
                generated["foreground"].append({"rect": rect, "id": pixel.b})

    return generated


def get_active_chunks(
    player, chapter_data, active_enemies, active_props, all_assets, current_chapter_name
):
    global master_layout_img, current_layout_path, master_lightmap_img, current_lightmap_path

    tile_size = chapter_data.get("tile_size", 16)
    chunk_w = chapter_data["chunk_size"]["width"]
    chunk_h = chapter_data["chunk_size"]["height"]

    layout_path = chapter_data.get("layout")
    if layout_path and layout_path != current_layout_path:
        master_layout_img = load_master(layout_path)
        current_layout_path = layout_path

    lightmap_master_path = chapter_data.get("lightmap")
    if lightmap_master_path and lightmap_master_path != current_lightmap_path:
        if os.path.exists(lightmap_master_path):
            master_lightmap_img = pygame.image.load(lightmap_master_path).convert()
            current_lightmap_path = lightmap_master_path

    chunk_x = player.rect.centerx // chunk_w
    chunk_y = player.rect.centery // chunk_h

    active_stuff = {
        "deco": [],
        "collision": [],
        "foreground": [],
        "lightmap": [],
    }

    p_x_in_chunk = player.rect.centerx % chunk_w
    p_y_in_chunk = player.rect.centery % chunk_h
    dx = 1 if p_x_in_chunk > chunk_w // 2 else -1
    dy = 1 if p_y_in_chunk > chunk_h // 2 else -1

    chunks_to_load = [
        (chunk_x, chunk_y),
        (chunk_x + dx, chunk_y),
        (chunk_x, chunk_y + dy),
        (chunk_x + dx, chunk_y + dy),
    ]

    for cur_x, cur_y in chunks_to_load:
        key = f"{cur_x},{cur_y}"

        if key not in chunk_cache:
            chunk_json_info = chapter_data["chunks"].get(key)

            if master_layout_img:
                generated = get_data_from_master(
                    master_layout_img, cur_x, cur_y, tile_size
                )

                if generated and master_lightmap_img:
                    try:
                        lm_rect = pygame.Rect(cur_x * 1280, cur_y * 720, 1280, 720)
                        raw_lm = master_lightmap_img.subsurface(lm_rect)

                        final_lm = pygame.transform.scale(raw_lm, (1280, 720)).convert()
                        generated["lightmap"] = final_lm
                    except ValueError:
                        generated["lightmap"] = None

                chunk_cache[key] = generated
            else:
                chunk_cache[key] = None

            if chunk_json_info:
                if current_chapter_name not in initialized_chunks:
                    initialized_chunks[current_chapter_name] = set()

                state = world_state.setdefault(
                    current_chapter_name,
                    {
                        "dead_enemies": set(),
                        "used_props": {},
                        "collected_items": set(),
                    },
                )

                if key not in initialized_chunks[current_chapter_name]:
                    initialized_chunks[current_chapter_name].add(key)

                    for enemy_data in chunk_json_info.get("enemies", []):
                        enemy_id = f"{key}_{enemy_data['type']}_{enemy_data['x']}_{enemy_data['y']}"
                        if enemy_id not in state["dead_enemies"]:
                            spawn_x = cur_x * chunk_w + enemy_data["x"]
                            spawn_y = cur_y * chunk_h + enemy_data["y"]
                            enemy_class = entity_types.get(enemy_data["type"])
                            if enemy_class:
                                new_enemy = enemy_class(spawn_x, spawn_y)
                                new_enemy.unique_id = enemy_id
                                active_enemies.append(new_enemy)

                    for p_data in chunk_json_info.get("props", []):
                        prop_id = f"{key}_{p_data['type']}_{p_data['x']}_{p_data['y']}"
                        spawn_x = cur_x * chunk_w + p_data["x"]
                        spawn_y = cur_y * chunk_h + p_data["y"]
                        prop_class = prop_types.get(p_data["type"])
                        if prop_class:
                            current_sprite = None
                            if p_data["type"] == "Collectable":
                                if prop_id in state["collected_items"]:
                                    continue
                                current_sprite = all_assets.get(p_data.get("name"))

                            prop_config = {
                                k: v
                                for k, v in p_data.items()
                                if k not in ["x", "y", "type", "width", "height"]
                            }
                            new_prop = prop_class(
                                spawn_x,
                                spawn_y,
                                p_data.get("width", 32),
                                p_data.get("height", 32),
                                assets=all_assets,
                                sprite=current_sprite,
                                **prop_config,
                            )
                            new_prop.unique_id = prop_id
                            active_props.append(new_prop)

        cached = chunk_cache.get(key)
        if cached:
            active_stuff["deco"].extend(cached["deco"])
            active_stuff["collision"].extend(cached["collision"])
            active_stuff["foreground"].extend(cached["foreground"])
            if cached["lightmap"]:
                lm_pos = (cur_x * chunk_w, cur_y * chunk_h)
                active_stuff["lightmap"].append((cached["lightmap"], lm_pos))

    return active_stuff


def refresh(internal_surf, real_window):
    scaled = pygame.transform.scale(internal_surf, real_window.get_size())
    real_window.blit(scaled, (0, 0))
    pygame.display.flip()


def draw_ui(screen, player, clock):
    font = pygame.font.SysFont("Courier New", 24, bold=True)

    fps = int(clock.get_fps())
    fps_color = "#00FF00" if fps > 45 else "#FFD900" if fps > 20 else "#FF0000"

    fps_text = font.render(f"FPS: {fps}", True, fps_color)
    health_text = font.render(f"HEALTH: {player.health}", True, "#1F767C89")
    shield_text = font.render(f"SHIELD: {player.shield}", True, "#1F767C89")
    weapon_color = "#1F767C89" if player.shoot_cooldown == 0 else "#44444489"
    weapon_name = "NONE"
    if player.inventory:
        weapon_name = player.inventory[player.weapon_selected]
    weapon_text = font.render(f"WEAPON: {weapon_name}", True, weapon_color)

    ui_y_start = 615

    screen.blit(fps_text, (1150, 10))
    screen.blit(health_text, (10, ui_y_start))
    screen.blit(shield_text, (10, ui_y_start + 35))
    screen.blit(weapon_text, (10, ui_y_start + 70))


def draw_game_over(screen):
    overlay = pygame.Surface((1280, 720))
    overlay.set_alpha(160)
    overlay.fill("#3B0505")
    screen.blit(overlay, (0, 0))

    font_big = pygame.font.SysFont("Courier New", 64, bold=True)
    font_small = pygame.font.SysFont("Courier New", 24, bold=True)

    line1 = font_big.render("SUBJECT: FREEMAN", True, "#FF0000")
    line2 = font_big.render("STATUS: TERMINATED", True, "#FF0000")
    line3 = font_small.render("PRESS SPACE TO RESTART", True, "#CCCCCC")

    screen.blit(line1, (640 - line1.get_width() // 2, 280))
    screen.blit(line2, (640 - line2.get_width() // 2, 360))
    screen.blit(line3, (640 - line3.get_width() // 2, 500))


def active_wait(ms):
    start_time = pygame.time.get_ticks()
    while pygame.time.get_ticks() - start_time < ms:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()


def play_intro(screen, real_window):
    font = pygame.font.SysFont("Courier New", 28, bold=True)

    script = [
        ("!!! KRITISCHER SYSTEMFEHLER !!!", 800),
        ("BIO-MONITOR: BENUTZER BEWUSSTLOS", 600),
        ("INITIERE NOTFALL-MODUS...", 1000),
        ("", 500),
        ("STANDORT: UNBEKANNT", 700),
        ("WARNUNG: EXTREME STRAHLUNG GEMESSEN", 700),
        ("", 300),
        ("WACH AUF, MR. FREEMAN.", 1200),
        ("ES IST NOCH NICHT VORBEI.", 3000),
        ("", 0),
        ("(SPACE)", 0),
    ]

    finished_lines = []

    for text_content, post_pause in script:
        display_text = ""

        for char in text_content:
            display_text += char
            screen.fill("#000000")

            for idx, line in enumerate(finished_lines):
                old_surf = font.render(line, True, "#00FF00")
                screen.blit(old_surf, (100, 100 + idx * 40))

            current_surf = font.render(display_text, True, "#00FF00")
            screen.blit(current_surf, (100, 100 + len(finished_lines) * 40))

            refresh(screen, real_window)

            active_wait(35)

        finished_lines.append(text_content)

        active_wait(post_pause)

    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                waiting = False

        refresh(screen, real_window)


def show_loading(screen, real_window):
    frozen_frame = screen.copy()

    overlay = pygame.Surface((1280, 720))
    overlay.set_alpha(160)
    overlay.fill("#000000")

    screen.blit(frozen_frame, (0, 0))
    screen.blit(overlay, (0, 0))

    font = pygame.font.SysFont("Courier New", 32, bold=True)
    line = font.render("LOADING...", True, "#FFD900")
    screen.blit(line, (640 - line.get_width() // 2, 360))

    refresh(screen, real_window)
    pygame.time.delay(250)


def get_save_name(screen, real_window):
    font = pygame.font.SysFont("Courier New", 32, bold=True)
    input_text = ""
    getting_name = True

    while getting_name:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    hwnd = pygame.display.get_wm_info()["window"]
                    ctypes.windll.user32.ShowWindow(hwnd, 3)
                    pygame.display.toggle_fullscreen()
                if event.key == pygame.K_RETURN and input_text.strip() != "":
                    getting_name = False
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                else:
                    if len(input_text) < 15 and event.unicode.isalnum():
                        input_text += event.unicode

        screen.fill("#3a3a3a")
        prompt = font.render("ENTER SAVE NAME:", True, "#FFD900")
        name_surf = font.render(f"> {input_text}_", True, "#FFFFFF")

        screen.blit(prompt, (640 - prompt.get_width() // 2, 300))
        screen.blit(name_surf, (640 - name_surf.get_width() // 2, 350))

        refresh(screen, real_window)

    return f"saves/{input_text}.json"


def main_menu(screen, real_window):
    font = pygame.font.SysFont("Courier New", 32, bold=True)
    title_font = pygame.font.SysFont("Courier New", 64, bold=True)

    if not os.path.exists("saves"):
        os.makedirs("saves")

    menu_running = True

    while menu_running:
        save_files = ["NEW GAME"] + [
            f for f in os.listdir("saves") if f.endswith(".json")
        ]
        options = save_files + ["QUIT"]

        m_x, m_y = pygame.mouse.get_pos()
        w_w, w_h = real_window.get_size()
        mouse_pos = (m_x * 1280 // w_w, m_y * 720 // w_h)
        mouse_clicked = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_clicked = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    hwnd = pygame.display.get_wm_info()["window"]
                    ctypes.windll.user32.ShowWindow(hwnd, 3)
                    pygame.display.toggle_fullscreen()

        screen.fill("#3a3a3a")

        title_line = title_font.render("HALF-LIFE: 2D", True, "#695E54")
        screen.blit(title_line, (640 - title_line.get_width() // 2, 100))

        for i, name in enumerate(options):
            text_str = name.replace(".json", "")

            text_surf_idle = font.render(f"  {text_str}", True, "#777777")
            text_rect = text_surf_idle.get_rect(topleft=(100, 250 + i * 45))

            if text_rect.collidepoint(mouse_pos):
                display_color = "#FFD900"
                prefix = "> "
                if mouse_clicked:
                    if name == "QUIT":
                        pygame.quit()
                        exit()
                    elif name == "NEW GAME":
                        return get_save_name(screen, real_window)
                    else:
                        return f"saves/{name}"
            else:
                display_color = "#777777"
                prefix = "  "

            final_text = font.render(f"{prefix}{text_str}", True, display_color)
            screen.blit(final_text, text_rect.topleft)

        refresh(screen, real_window)


def mainloop(screen, real_window):
    global world_state, chunk_cache, initialized_chunks

    chunk_cache.clear()
    initialized_chunks.clear()

    selected_save_path = main_menu(screen, real_window)

    clock = pygame.time.Clock()
    running = True

    current_chapter_file = "chapters/chapter1.json"
    loaded_data = None

    if selected_save_path:
        loaded_data = load_game(selected_save_path)

    if loaded_data:
        world_state = loaded_data["world_state"]
        current_chapter_file = loaded_data["current_chapter"]
        p_data = loaded_data["player"]
        player = Player(p_data["x"], p_data["y"])
        player.health = p_data["health"]
        player.shield = p_data["shield"]
        player.inventory = p_data["inventory"]
        player.weapon_selected = p_data["weapon_selected"]
        chunk_cache.clear()
        initialized_chunks.clear()
    else:
        world_state.clear()
        chunk_cache.clear()
        initialized_chunks.clear()
        if selected_save_path != "saves/DEBUG.json":
            play_intro(screen, real_window)
        chapter_data = load_chapter(current_chapter_file)
        player = Player(
            chapter_data["spawn_pos"][0],
            chapter_data["spawn_pos"][1],
        )

    chapter_data = load_chapter(current_chapter_file)
    all_enemies = []
    all_props = []
    all_particles = []
    camera = Camera(1280, 720)

    prop_assets = load_prop_assets()
    weapon_assets = load_weapon_assets()
    tilesheet = SpriteSheet("spritesheets/tilesheet.png")
    tile_size = 16

    tile_textures = {
        0: tilesheet.get_image(112, 112, tile_size, tile_size),  # Fehlende Textur
        255: tilesheet.get_image(0, 0, tile_size, tile_size),  # Metall
        245: tilesheet.get_image(16, 0, tile_size, tile_size),  # Orange
        235: tilesheet.get_image(32, 0, tile_size, tile_size),  # Absperrband
        225: tilesheet.get_image(48, 0, tile_size, tile_size),  # Gitter
        215: tilesheet.get_image(64, 0, tile_size, tile_size),  # Unten Hälfte
        205: tilesheet.get_image(80, 0, tile_size, tile_size),  # Oben Hälfte
        195: tilesheet.get_image(96, 0, tile_size, tile_size),  # Stangen
        185: tilesheet.get_image(112, 0, tile_size, tile_size),  # Dunkel
        175: tilesheet.get_image(0, 16, tile_size, tile_size),  # Säure
        165: tilesheet.get_image(16, 16, tile_size, tile_size),  # Stachel
    }

    fog_surface = pygame.Surface((1280, 720))

    show_loading(screen, real_window)

    while running:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    hwnd = pygame.display.get_wm_info()["window"]
                    ctypes.windll.user32.ShowWindow(hwnd, 3)
                    pygame.display.toggle_fullscreen()

                if event.key == pygame.K_F6:
                    save_game(
                        player, current_chapter_file, world_state, selected_save_path
                    )

                if event.key == pygame.K_ESCAPE:
                    mainloop(screen, real_window)
                    return

            if player.health <= 0:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        loaded_data = (
                            load_game(selected_save_path)
                            if selected_save_path
                            else None
                        )

                        if loaded_data:
                            world_state = loaded_data["world_state"]
                            current_chapter_file = loaded_data["current_chapter"]
                            chapter_data = load_chapter(current_chapter_file)
                            p_data = loaded_data["player"]
                            player = Player(p_data["x"], p_data["y"])
                            player.health = p_data["health"]
                            player.shield = p_data["shield"]
                            player.inventory = p_data["inventory"]
                            player.weapon_selected = p_data["weapon_selected"]
                        else:
                            world_state.clear()
                            current_chapter_file = "chapters/chapter1.json"
                            chapter_data = load_chapter(current_chapter_file)
                            player = Player(
                                chapter_data["spawn_pos"][0],
                                chapter_data["spawn_pos"][1],
                            )
                            player.health = 100
                            player.inventory = []

                        chunk_cache.clear()
                        all_enemies = []
                        all_props = []
                        all_particles = []
                        camera = Camera(1280, 720)
                        show_loading(screen, real_window)

        if player.health > 0:
            keys = pygame.key.get_pressed()
            all_objects = get_active_chunks(
                player,
                chapter_data,
                all_enemies,
                all_props,
                prop_assets | weapon_assets,
                current_chapter_file,
            )

            chunk_w = chapter_data["chunk_size"]["width"]
            chunk_h = chapter_data["chunk_size"]["height"]
            p_chunk_x = player.rect.centerx // chunk_w
            p_chunk_y = player.rect.centery // chunk_h

            for enemy in all_enemies:
                e_chunk_x = enemy.rect.centerx // chunk_w
                e_chunk_y = enemy.rect.centery // chunk_h
                if abs(e_chunk_x - p_chunk_x) <= 1 and abs(e_chunk_y - p_chunk_y) <= 1:
                    enemy.update(all_objects, player)

            for prop in all_props:
                pr_chunk_x = prop.rect.centerx // chunk_w
                pr_chunk_y = prop.rect.centery // chunk_h

                if (
                    abs(pr_chunk_x - p_chunk_x) <= 1
                    and abs(pr_chunk_y - p_chunk_y) <= 1
                ):
                    if not getattr(prop, "is_loading_zone", False):
                        prop.update(all_objects)

            for particle in all_particles:
                particle.update(all_objects)

            all_particles = [p for p in all_particles if p.life > 0]

            if keys[pygame.K_e]:
                for prop in all_props:
                    if player.rect.colliderect(prop.rect):
                        prop.interact(player)
                        if isinstance(prop, Collectable):
                            chapter_state = world_state[current_chapter_file]
                            if "collected_items" not in chapter_state:
                                chapter_state["collected_items"] = set()

                            chapter_state["collected_items"].add(prop.unique_id)

                            all_props.remove(prop)
                            break

            player.update(keys, all_objects, all_enemies, all_particles)
            camera.update(player)

            if player.check_loading_zone((all_props)):
                chunk_w = chapter_data["chunk_size"]["width"]
                chunk_h = chapter_data["chunk_size"]["height"]

                current_x = player.rect.centerx // chunk_w
                current_y = player.rect.centery // chunk_h
                chunk_key = f"{current_x},{current_y}"
                chunk_info = chapter_data["chunks"].get(chunk_key)

                if chunk_info and "loading_zones" in chunk_info:
                    target_id = "1"
                    for p in all_props:
                        if getattr(
                            p, "is_loading_zone", False
                        ) and player.rect.colliderect(p.rect):
                            target_id = getattr(p, "target_id", "1")
                            break

                    next_file = chunk_info["loading_zones"].get(target_id)
                    if next_file:
                        show_loading(screen, real_window)

                        current_chapter_file = next_file
                        chapter_data = load_chapter(next_file)

                        player.rect.x = chapter_data["spawn_pos"][0]
                        player.rect.y = chapter_data["spawn_pos"][1]

                        chunk_cache.clear()
                        if current_chapter_file in initialized_chunks:
                            initialized_chunks[current_chapter_file].clear()
                        all_enemies = []
                        all_props = []
                        continue

            if current_chapter_file not in world_state:
                world_state[current_chapter_file] = {
                    "dead_enemies": set(),
                    "used_props": {},
                }

            for e in all_enemies:
                if e.is_dead and hasattr(e, "unique_id"):
                    if abs(particle.rect.x - player.rect.x) < 750:
                        p_color = "#FF0000"
                        if isinstance(e, Headcrab):
                            p_color = "#B9B965"
                        for _ in range(16):
                            all_particles.append(
                                Particle(e.rect.centerx, e.rect.centery, 4, p_color)
                            )
                    world_state[current_chapter_file]["dead_enemies"].add(e.unique_id)

            for p in all_props:
                if hasattr(p, "unique_id") and hasattr(p, "charges"):
                    world_state[current_chapter_file]["used_props"][
                        p.unique_id
                    ] = p.charges

            all_enemies = [e for e in all_enemies if not e.is_dead]

        screen.fill("#1a1a1a")

        for tile in all_objects["deco"]:
            tex = tile_textures.get(tile["id"], tile_textures[0])
            screen.blit(tex, camera.apply(tile["rect"]))

        for tile in all_objects["collision"]:
            tex = tile_textures.get(tile["id"], tile_textures[0])
            screen.blit(tex, camera.apply(tile["rect"]))

        for prop in all_props:
            prop.draw(screen, camera)
        for enemy in all_enemies:
            enemy.draw(screen, camera)
        for particle in all_particles:
            particle.draw(screen, camera)
        player.draw(screen, camera)

        for tile in all_objects["foreground"]:
            tex = tile_textures.get(tile["id"], tile_textures[0])
            screen.blit(tex, camera.apply(tile["rect"]))

        for lm_img, pos in all_objects["lightmap"]:
            lm_rect = pygame.Rect(pos[0], pos[1], 1280, 720)
            screen_pos = camera.apply(lm_rect)
            screen.blit(lm_img, screen_pos, special_flags=pygame.BLEND_MULT)

        if player.health > 0:
            draw_ui(screen, player, clock)
        else:
            draw_game_over(screen)

        refresh(screen, real_window)

    pygame.quit()


if __name__ == "__main__":
    screen, internal_surface = init()
    mainloop(internal_surface, screen)
