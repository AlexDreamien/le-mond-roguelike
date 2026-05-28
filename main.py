"""Browser entry point for the pygbag/WASM build.

pygbag runs this top-level module and patches ``asyncio.run`` to drive the
browser's event loop. The game's coroutines yield with ``await asyncio.sleep(0)``
each frame so the page stays responsive.

Any startup error is painted onto the canvas (and printed) instead of leaving a
blank grey screen, since pygbag sends Python tracebacks to its own terminal
rather than the browser's JS console.

Desktop users should launch ``start.py`` (or ``python -m lemond_pygame``) instead;
both ultimately call the same ``lemond_pygame.game.run`` coroutine.
"""

import asyncio
import traceback

import pygame as pg

from lemond_pygame.game import run


def _wrap(text, width=96):
    return [text[i : i + width] for i in range(0, len(text), width)] or [""]


def _show_error(tb: str) -> None:
    print(tb)  # also surfaces in the pygbag terminal / JS console
    try:
        pg.font.init()
        surface = pg.display.get_surface()
        if surface is None:
            return
        surface.fill((12, 10, 18))
        font = pg.font.Font(None, 22)
        y = 14
        for raw in tb.splitlines():
            for chunk in _wrap(raw):
                surface.blit(font.render(chunk, True, (255, 150, 150)), (12, y))
                y += 22
        pg.display.flip()
    except Exception:
        pass


async def _main() -> None:
    try:
        await run()
    except Exception:
        _show_error(traceback.format_exc())
        while True:  # keep the error frame on screen
            await asyncio.sleep(0.25)


asyncio.run(_main())
