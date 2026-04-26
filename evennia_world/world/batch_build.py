"""
Batch build script for LLMud Institute initial rooms.

Run from CLI (while Evennia is running):
    cd evennia_world && .venv/bin/python -c "
    import django, os, sys
    os.environ['DJANGO_SETTINGS_MODULE'] = 'server.conf.settings'
    sys.path.insert(0, '.')
    django.setup()
    from world.batch_build import build
    build()
    "

Creates:
- Observer Hub (renamed Limbo)
- Researcher's Lab (connected via exit, locked to Builder+)
- Polysemy Observatory (MicroWorldRoom with preset config)
"""

from evennia import create_object, search_object
from evennia.utils import logger


def build():
    """Create the initial room layout."""

    # Find or rename Limbo (Evennia's default starting room, #2)
    limbo = search_object("#2")
    if limbo:
        hub = limbo[0]
        hub.key = "Observer Hub"
        hub.db.desc = (
            "The central nexus of the LLMud Institute. Corridors branch off "
            "toward research labs and micro-world observatories. A soft hum of "
            "computation fills the air.\n\n"
            "Exits: lab"
        )
        hub.db.room_type = "hub"
        # Swap typeclass to our Room
        hub.swap_typeclass("typeclasses.rooms.Room", clean_attributes=False)
        logger.log_info("Observer Hub configured (room #2)")
    else:
        logger.log_err("Could not find Limbo (#2)")
        return

    # Create Researcher's Lab if it doesn't exist
    existing_lab = search_object("Researcher's Lab")
    if existing_lab:
        lab = existing_lab[0]
        logger.log_info("Researcher's Lab already exists")
    else:
        lab = create_object(
            "typeclasses.rooms.ResearcherLab",
            key="Researcher's Lab",
        )
        lab.db.desc = (
            "Your personal research workspace. The viz panels on the walls respond "
            "to your commands, displaying expert routing flows and attractor basin "
            "dynamics. You have full control here.\n\n"
            "Exits: hub"
        )
        logger.log_info(f"Created Researcher's Lab ({lab.dbref})")

    # Create exits between Hub and Lab (if they don't exist)
    existing_exits = [obj for obj in hub.contents if obj.key == "lab" and obj.destination == lab]
    if not existing_exits:
        create_object(
            "evennia.objects.objects.DefaultExit",
            key="lab",
            location=hub,
            destination=lab,
            locks="traverse:perm(Builder)",
        )
        logger.log_info("Created exit: Hub → Lab (locked to Builder+)")
    else:
        existing_exits[0].locks.add("traverse:perm(Builder)")
        logger.log_info("Updated lab exit lock: traverse:perm(Builder)")

    existing_exits = [obj for obj in lab.contents if obj.key == "hub" and obj.destination == hub]
    if not existing_exits:
        create_object(
            "evennia.objects.objects.DefaultExit",
            key="hub",
            location=lab,
            destination=hub,
        )
        logger.log_info("Created exit: Lab → Hub")

    # Create Polysemy Observatory (MicroWorldRoom) if it doesn't exist
    existing_obs = search_object("Polysemy Observatory")
    if existing_obs:
        obs = existing_obs[0]
        logger.log_info("Polysemy Observatory already exists")
    else:
        obs = create_object(
            "typeclasses.rooms.MicroWorldRoom",
            key="Polysemy Observatory",
        )
        obs.db.desc = (
            "An observatory dedicated to studying polysemous words — tokens that "
            "shift meaning based on context. The viz panels display how the model's "
            "internal representations route differently for the same surface form.\n\n"
            "Exits: hub"
        )
        obs.db.world_config = {
            "session_id": "session_1434a9be",
            "clustering_schema": "polysemy_explore",
            "viz_preset": {
                "primary_axis": "label",
                "gradient": "red-blue",
                "window": "w0",
                "clustering_schema": "polysemy_explore",
                "top_routes": 10,
            },
        }
        logger.log_info(f"Created Polysemy Observatory ({obs.dbref})")

    # Hub exits description update
    hub.db.desc = (
        "The central nexus of the LLMud Institute. Corridors branch off "
        "toward research labs and micro-world observatories. A soft hum of "
        "computation fills the air.\n\n"
        "Exits: lab, polysemy"
    )

    # Create exits to/from Observatory
    existing_exits = [obj for obj in hub.contents if obj.key == "polysemy" and obj.destination == obs]
    if not existing_exits:
        create_object(
            "evennia.objects.objects.DefaultExit",
            key="polysemy",
            location=hub,
            destination=obs,
        )
        logger.log_info("Created exit: Hub → Polysemy Observatory")

    existing_exits = [obj for obj in obs.contents if obj.key == "hub" and obj.destination == hub]
    if not existing_exits:
        create_object(
            "evennia.objects.objects.DefaultExit",
            key="hub",
            location=obs,
            destination=hub,
        )
        logger.log_info("Created exit: Polysemy Observatory → Hub")

    logger.log_info("Batch build complete.")
