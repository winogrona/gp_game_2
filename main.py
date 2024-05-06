import socket
import logging
import asyncio

import kahoot2 as libkahoot
import kahoot_integration

import pygame # type: ignore
import qrcode # type: ignore

from sys import argv
from threading import Thread
from queue import Queue
from typing import Any

from qr_screen import qr_screen

logging.basicConfig(level=logging.INFO)

if len(argv) < 2:
    logging.error("Pass the WIFI SSID in the first argument ans then we'll talk")
    exit(1)

SSID = argv[1]

server = libkahoot.Server()
kahoot_queue: Queue[Any] = Queue()

loop = asyncio.new_event_loop()

def start_background_loop(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    loop.run_forever()

async def libkahoot_main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting the kahoot server")
    kahoot_integration.setup_callbacks(kahoot_queue, server.game)
    await server.start(8080)

kahoot_thread = Thread(target=start_background_loop, args=[loop], daemon=True)
kahoot_thread.start()
asyncio.run_coroutine_threadsafe(libkahoot_main(), loop)

pygame.init()

display_info = pygame.display.Info()

logging.info(f"Display size: {display_info.current_w}x{display_info.current_h}")

SCREEN = pygame.display.set_mode((1400, 1000))#, pygame.FULLSCREEN)

#SCREEN = pygame.display.set_mode((display_info.current_w, display_info.current_h), pygame.FULLSCREEN)
pygame.display.set_caption("Subscribe to @neomiusli on Telegram")

LOCAL_IP = socket.gethostbyname(socket.gethostname())
logging.info(f"Local IP: {LOCAL_IP}")

qr_screen(SCREEN, SSID, LOCAL_IP, kahoot_queue, server.game)