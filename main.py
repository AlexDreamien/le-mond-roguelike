"""Browser entry point for the pygbag/WASM build.

pygbag runs this top-level module and patches ``asyncio.run`` to drive the
browser's event loop. The game's coroutines yield with ``await asyncio.sleep(0)``
each frame so the page stays responsive.

Desktop users should launch ``start.py`` (or ``python -m lemond_pygame``) instead;
both ultimately call the same ``lemond_pygame.game.run`` coroutine.
"""

import asyncio

from lemond_pygame.game import run

asyncio.run(run())
