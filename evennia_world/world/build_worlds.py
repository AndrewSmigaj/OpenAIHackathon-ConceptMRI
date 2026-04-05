"""
Build micro-world rooms from YAML config files.

Usage:
    cd evennia_world
    ../.venv/bin/python -c "
    import os, sys, django
    os.environ['DJANGO_SETTINGS_MODULE'] = 'server.conf.settings'
    sys.path.insert(0, os.getcwd())
    django.setup()
    import evennia; evennia._init()
    from world.build_worlds import build_all
    build_all()
    "

Reads YAML files from data/worlds/ and creates/updates MicroWorldRoom
instances with the configured session, schema, and viz preset.
Idempotent — safe to re-run after editing YAML files.
"""

import os
import yaml
from evennia import create_object, search_object


WORLDS_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', 'data', 'worlds'
)


def build_room(config: dict) -> None:
    """Create or update a single micro-world room from config."""
    name = config['name']
    hub = search_object('#2')
    if not hub:
        print(f'ERROR: Could not find Hub (#2)')
        return
    hub = hub[0]

    # Find or create the room
    existing = search_object(name)
    if existing:
        room = existing[0]
        print(f'Updating: {name} ({room.dbref})')
    else:
        room = create_object('typeclasses.rooms.MicroWorldRoom', key=name)
        print(f'Created: {name} ({room.dbref})')

    # Ensure typeclass
    if room.typeclass_path != 'typeclasses.rooms.MicroWorldRoom':
        room.swap_typeclass('typeclasses.rooms.MicroWorldRoom', clean_attributes=False)

    # Set description
    room.db.desc = config.get('description', f'{name}\n\nExits: hub')

    # Set world config (consumed by at_object_receive for OOB events)
    room.db.world_config = {
        'session_id': config.get('session_id'),
        'clustering_schema': config.get('clustering_schema'),
        'role': config.get('role', 'visitor'),
        'viz_preset': config.get('viz_preset', {}),
    }

    # Create exit name (lowercase, no spaces)
    exit_key = name.lower().replace(' ', '_').replace("'", '')

    # Create exit from Hub to room (if not exists)
    existing_exits = [obj for obj in hub.contents
                      if hasattr(obj, 'destination') and obj.destination == room]
    if not existing_exits:
        create_object(
            'evennia.objects.objects.DefaultExit',
            key=exit_key,
            location=hub,
            destination=room,
        )
        print(f'  Created exit: Hub -> {name} ("{exit_key}")')

    # Create exit from room back to Hub (if not exists)
    existing_exits = [obj for obj in room.contents
                      if hasattr(obj, 'destination') and obj.destination == hub]
    if not existing_exits:
        create_object(
            'evennia.objects.objects.DefaultExit',
            key='hub',
            location=room,
            destination=hub,
        )
        print(f'  Created exit: {name} -> Hub')


def build_all() -> None:
    """Build all micro-world rooms from YAML files in data/worlds/."""
    worlds_dir = os.path.abspath(WORLDS_DIR)
    if not os.path.isdir(worlds_dir):
        print(f'No worlds directory found at {worlds_dir}')
        return

    yaml_files = sorted(f for f in os.listdir(worlds_dir) if f.endswith('.yaml'))
    if not yaml_files:
        print('No YAML world configs found')
        return

    print(f'Building {len(yaml_files)} world(s) from {worlds_dir}')
    for filename in yaml_files:
        filepath = os.path.join(worlds_dir, filename)
        with open(filepath) as f:
            config = yaml.safe_load(f)
        if config and 'name' in config:
            build_room(config)
        else:
            print(f'Skipping {filename} — missing "name" field')

    print('World build complete.')
