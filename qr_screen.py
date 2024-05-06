import pygame # type: ignore
import qrcode # type: ignore

import logging
import io
import kahoot2

from style import *

from queue import Queue
from typing import Any

def qr_tile(qr_string: str, caption_text: str) -> pygame.Surface:
    qr_img = qrcode.make(qr_string)
    raw_img = qr_img.convert("RGB").tobytes("raw", "RGB")
    qr_surface = pygame.image.fromstring(raw_img, qr_img.size, "RGB")
    (qr_w, qr_h) = qr_surface.get_size()

    text_surface = heading2(caption_text)
    text_rect = text_surface.get_rect(center=(qr_w / 2, qr_h))

    (text_w, text_h) = text_surface.get_size()

    tile_surface = pygame.Surface((qr_w + text_w + 10, qr_h))
    tile_surface.fill("White")
    tile_surface.blit(qr_surface, (0, 0))
    tile_surface.blit(text_surface, (qr_w + 10, qr_h * 0.25))

    return tile_surface

def qr_screen(screen: pygame.Surface, SSID: str, ip: str, kahoot_queue: Queue[Any], game: kahoot2.Game) -> None:
    game.accepting_new_players = True
    screen.fill("white")

    (screen_w, screen_h) = screen.get_size()

    wifi_string = f"WIFI:S:{SSID};T:nopass;P:;H:false;;"

    base_h = 100

    first_tile = qr_tile(wifi_string, "1. Przeskanuj i podłacz się do WIFi")
    (first_tile_w, first_tile_h) = first_tile.get_size()
    second_tile = qr_tile(f"http://{ip}:8080/res/index.html", "2. Przeskanuj i przejdz na stronę")
    (second_tile_w, second_tile_h) = second_tile.get_size()

    base_w = screen_w / 2 - first_tile_w / 2

    screen.blit(first_tile, (base_w, base_h))
    screen.blit(second_tile, (base_w, base_h + first_tile_h))

    players_surface = pygame.Surface((screen_w - 40, screen_h - 50))

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
    
        players_surface.fill("White")
        players_surface.blit(content(f"Gracze({len(game.players)}): " + ", ".join([player.name for player in game.players])), (0, 0))
        screen.blit(players_surface, (20, base_h + first_tile_h + second_tile_h))
        pygame.display.update()