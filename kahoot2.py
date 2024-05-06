import asyncio
import json
import logging

import aiohttp

from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Optional
from typing import Callable
from inspect import iscoroutinefunction
from enum import Enum
from time import time

from aiohttp import web

@dataclass
class Player:
    name: str
    ip_addr: str
    score: int = field(default=0)
    answered_last_question: bool = field(default=False)

@dataclass
class Game:
    reward_points: int = field(default=500, init=True)
    reward_bonus: int = field(default=700, init=True)
    reward_bonus_time_multiplier: float = field(default=0.93, init=True)

    question_is_being_asked: bool = field(default=False)
    time_since_last_question: float = field(default=0)
    question_answer_variants: int = field(default=0)
    question_correct_answers: list[int] = field(default_factory=lambda: list())
    accepting_new_players: bool = field(default=False)

    on_player_registered: Callable[[Player], []] = field(default=lambda x: None)
    on_player_unregistered: Callable[[Player], []] = field(default=lambda x: None)
    on_player_made_a_guess: Callable[[Player, bool], []] = field(default=lambda x, y: None)

    players: list[Player] = field(default_factory=lambda: [])
    connections: list["Connection"] = field(default_factory=lambda: [])

    @staticmethod
    async def send_question_event(connection: "Connection", number_of_variants: int) -> None:
        await connection.send_event(Event(
                "question",
                {
                    "number_of_variants": number_of_variants
                }
            ))

    async def ask_a_question(self, number_of_variants: int, correct_answers: list[int]) -> None:
        self.question_is_being_asked = True
        self.question_answer_variants = number_of_variants
        self.question_correct_answers = correct_answers

        self.time_at_last_question = time()

        for connection in self.connections:
            if connection.player is None:
                continue

            connection.player.answered_last_question = False

            try:
                await self.send_question_event(connection, number_of_variants)
            except ConnectionResetError as e:
                logging.error(f"Failed to send an event: {e}")
    
    async def new_connection(self, connection: "Connection") -> None:
        self.connections.append(connection)

        for player in self.players:
            if player.ip_addr == connection.ip_addr:
                connection.player = player
                break

        await connection.send_status()

@dataclass
class Event:
    event_type: str
    args: dict[str, Any] = field(default_factory=lambda: {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "args": self.args
        }
    
    @staticmethod
    def from_dict(source: dict[str, Any]) -> "Event":
        return Event(
            event_type=source["event_type"],
            args = source["args"]
        )
    @staticmethod
    def error(text: str) -> "Event":
        return Event(
            event_type="error",
            args={
                "text": text
            }
        )

async def run_callable_maybe_coroutine(callable: Optional[Callable[..., ...]], *args: Any, **kwargs: Any) -> Any:
    if callable is None:
        return

    if iscoroutinefunction(callable):
        return await callable(*args, **kwargs)
    else:
        return callable(*args, **kwargs)

class Connection:
    connection: web.WebSocketResponse
    ip_addr: str
    player: Optional[Player]
    game: Game

    def __init__(self, connection: web.WebSocketResponse, ip_addr: str, game: Game):
        self.connection = connection
        self.ip_addr = ip_addr
        self.player = None
        self.game = game
    
    async def send_status(self) -> None:
        if self.player is not None:
            await self.send_event(Event("status", {
                "registered": True
            }))

            if self.game.question_is_being_asked and self.player.answered_last_question == False:
                await self.game.send_question_event(self, self.game.question_answer_variants)
        else:
            await self.send_event(Event("status", {
                "registered": False
            }))

    async def send_event(self, event: Event) -> None:
        await self.connection.send_json(Event(
            event_type=event.event_type,
            args=event.args
        ).to_dict())
    
    async def close(self, reason: str = "unknown error") -> None:
        await self.send_event(Event("connection_closed", {
            "reason": reason
        }))
        await self.connection.close()

    async def recv_event(self, event: Event) -> None:
        if event.event_type == "register":
            if self.player is not None:
                await self.send_event(Event.error("Failed to register: already registered"))
                return
            
            if not self.game.accepting_new_players:
                await self.send_event(Event.error("Failed to register: the game is not accepting new players"))
                return

            self.player = Player(event.args["name"], ip_addr=self.ip_addr)
            self.game.players.append(self.player)
            await run_callable_maybe_coroutine(self.game.on_player_registered, self.player)
            await self.send_status()
        
        elif event.event_type == "unregister":
            if self.player is None:
                await self.send_event(Event.error("Failed to unregister: not registered"))
                return
            
            self.game.players.remove(self.player)
            self.player = None

            await run_callable_maybe_coroutine(self.game.on_player_unregistered, self.player)
            await self.send_status()
        
        elif event.event_type == "guess":
            if self.player is None:
                await self.send_event(Event.error("Failed to guess: not registered"))
                await self.send_status()
                return
            
            if not self.game.question_is_being_asked:
                await self.send_event(Event.error("No question is being asked at the moment"))
                await self.send_event(Event("guessed", {
                    "score": self.player.score,
                    "correct": False
                }))
                return
            
            self.player.answered_last_question = True
            correct = event.args["variant"] in self.game.question_correct_answers
            await run_callable_maybe_coroutine(self.game.on_player_made_a_guess, self.player, correct)

            if correct:
                self.player.score += self.game.reward_points

                time_delta = time() - self.game.time_at_last_question

                multiplier = 1 if time_delta < 1 else self.game.reward_bonus_time_multiplier / time_delta
                bonus = self.game.reward_bonus * multiplier

                logging.info(f"Calculating bonus points for [{self.player}]: time_delta={time_delta}, multiplier={multiplier}, bonus={bonus}")

                self.player.score += int(bonus)
            
            await self.send_event(Event("guessed", {
                "score": self.player.score,
                "correct": correct
            }))

@dataclass
class Server:
    resources_path: str = field(default="./res")
    app: web.Application = field(default_factory=lambda: web.Application())

    game: Game = field(default_factory=lambda: Game(), init=False)

    def __post_init__(self) -> None:
        routes = web.RouteTableDef()

        @routes.get("/favicon.ico")
        async def favicon_getter(request: web.Request) -> web.FileResponse:
            raise web.HTTPMovedPermanently(location="/res/favicon.ico")
        
        routes.static("/res", self.resources_path + "/")

        @routes.get("/")
        async def index_getter(request: web.Request) -> web.FileResponse:
            raise web.HTTPMovedPermanently(location="/res/index.html")

        @routes.get("/ws")
        async def ws_handler(request: web.Request) -> web.WebSocketResponse:
            socket = web.WebSocketResponse()
            await socket.prepare(request)

            assert request.remote is not None

            connection = Connection(
                connection=socket,
                ip_addr=request.remote,
                game=self.game
            )

            await self.game.new_connection(connection)

            async for msg in socket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await connection.recv_event(Event.from_dict(json.loads(msg.data)))

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logging.error(f"Received an error message: {msg.data}")

            return socket
        
        self.app.add_routes(routes)

    async def start(self, port: int) -> None:
        runner = aiohttp.web.AppRunner(self.app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, port=port)
        await site.start()

async def setup_test_server(server: Server) -> None:
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting a test server")
    asyncio.create_task(server.start(1488))

def setup_simple_callbacks(game: Game) -> None:
    game.on_player_made_a_guess = lambda player, variant: print(f"Player [{player}] made a guess [{variant}]")
    game.on_player_registered = lambda player: print(f"A new player has registered: [{player}]")
    game.on_player_unregistered = lambda player: print(f"Player [{player}] has unregistered")