import pygame # type: ignore

def get_font(size: int) -> pygame.font.Font:
    return pygame.font.Font("assets/font.ttf", size)

def heading(text: str) -> pygame.Surface:
    return get_font(45).render(text, True, "Black")

def heading2(text: str) -> pygame.Surface:
    return get_font(25).render(text, True, "Black")

def caption(text: str) -> pygame.Surface:
    return get_font(7).render(text, True, "Black")

def content(text: str) -> pygame.Surface:
    return get_font(15).render(text, True, "Black")
