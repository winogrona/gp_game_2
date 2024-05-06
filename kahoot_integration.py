from queue import Queue
from enum import Enum
from typing import Any

import kahoot2 as libkahoot

class KahootEvent:
    PLAYER_REGISTERED = 0
    PLAYER_UNREGISTERED = 1
    PLAYER_MADE_A_GUESS = 2

def setup_callbacks(queue: Queue[Any], game: libkahoot.Game) -> None:
    game.on_player_made_a_guess = lambda player, correctness: queue.put((KahootEvent.PLAYER_MADE_A_GUESS, (player, correctness)))
    game.on_player_registered = lambda player: queue.put((KahootEvent.PLAYER_REGISTERED, (player)))
    game.on_player_unregistered = lambda player: queue.put((KahootEvent.PLAYER_UNREGISTERED, (player)))
