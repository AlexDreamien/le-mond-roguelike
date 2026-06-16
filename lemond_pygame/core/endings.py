"""The five endings and how Rosmund's final choice resolves to one.

Most endings map straight from the choice the player makes at the Heart; the
"destroy" choice splits into sealing-with-the-Inquisition vs. simply unwriting
the engine, decided by how much Inquisition favor the hero has earned.

Pure logic; the ending screen text lives under ``ending.<id>.*`` in the locales.
See docs/STORY.md section 3.
"""

from __future__ import annotations

SEIZE = "seize"  # become a fixture of Le-Mond, omnipotent inside, gone outside
DESTROY = "destroy"  # unwrite the engine; the Darkness dissipates; you can leave
SEAL = "seal"  # side with the Inquisition: seal the city with you as its warden
CULT = "cult"  # let the Darkness finish reading the world
REDEEM = "redeem"  # finish Rosmund's edit; someone walks out of Le-Mond intact

ALL = (SEIZE, DESTROY, SEAL, CULT, REDEEM)

INQ_FAVOR_TO_SEAL = 2  # this much Inquisition favor turns a "destroy" choice into a seal


def resolve(choice: str, hero) -> str:
    """Map a Rosmund dialogue ending token + hero state to a concrete ending id."""
    if choice == "destroy":
        return SEAL if hero.flags.get("inq_favor", 0) >= INQ_FAVOR_TO_SEAL else DESTROY
    return choice
