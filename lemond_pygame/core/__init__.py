"""Pure game logic with no PyGame dependency.

Everything in this package is deterministic, headless, and unit-testable:
dungeon generation, entities, combat math, field of view, and loot resolution.
The rendering, audio, input, and UI layers live outside ``core`` and depend on
it, never the other way around.
"""
