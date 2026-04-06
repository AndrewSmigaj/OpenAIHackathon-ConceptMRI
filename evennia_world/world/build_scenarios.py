"""
Build scenario rooms, NPCs, and objects from YAML config files.

Usage:
    cd evennia_world
    ../.venv/bin/python -c "
    import os, sys, django
    os.environ['DJANGO_SETTINGS_MODULE'] = 'server.conf.settings'
    sys.path.insert(0, os.getcwd())
    django.setup()
    import evennia; evennia._init()
    from world.build_scenarios import build_all_scenarios
    build_all_scenarios()
    "

Reads YAML files from data/worlds/scenarios/ and creates/updates
rooms, NPCs, and objects. Idempotent — safe to re-run.
"""

import os
import yaml
from evennia import create_object, search_object


SCENARIOS_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', 'data', 'worlds', 'scenarios'
)


def build_scenario(config):
    """Create or update rooms, NPCs, and objects for a scenario."""
    scenario_name = config['name']
    print(f"\nBuilding scenario: {scenario_name}")

    hub = search_object('#2')
    if not hub:
        print('  ERROR: Could not find Hub (#2)')
        return
    hub = hub[0]

    rooms_by_name = {}

    # 1. Create rooms
    for room_config in config.get('rooms', []):
        room_name = room_config['name']
        existing = search_object(room_name)
        if existing:
            room = existing[0]
            print(f'  Updating room: {room_name} ({room.dbref})')
        else:
            room = create_object('typeclasses.rooms.Room', key=room_name)
            print(f'  Created room: {room_name} ({room.dbref})')

        # Set description (include ambient text)
        desc = room_config.get('description', '').strip()
        ambient = room_config.get('ambient', [])
        if ambient:
            desc += '\n\n' + '\n'.join(ambient)
        room.db.desc = desc
        room.db.scenario_id = scenario_name

        rooms_by_name[room_name] = room

        # Create exit from Hub to room (if not exists)
        exit_key = room_name.lower().replace(' ', '_').replace("'", '')
        existing_exits = [obj for obj in hub.contents
                          if hasattr(obj, 'destination') and obj.destination == room]
        if not existing_exits:
            create_object(
                'evennia.objects.objects.DefaultExit',
                key=exit_key,
                location=hub,
                destination=room,
            )
            print(f'    Created exit: Hub -> {room_name} ("{exit_key}")')

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
            print(f'    Created exit: {room_name} -> Hub')

        # Create objects in room
        for obj_config in room_config.get('objects', []):
            obj_name = obj_config['name']
            existing_objs = [o for o in room.contents
                             if o.key.lower() == obj_name.lower()
                             and not hasattr(o, 'destination')]
            if existing_objs:
                obj = existing_objs[0]
                print(f'    Updating object: {obj_name}')
            else:
                obj = create_object('typeclasses.objects.Object', key=obj_name, location=room)
                print(f'    Created object: {obj_name}')
            obj.db.desc = obj_config.get('examine', obj_name)
            obj.db.examine_desc = obj_config.get('examine', '')

    # 2. Create inter-room exits
    for room_config in config.get('rooms', []):
        room = rooms_by_name.get(room_config['name'])
        if not room:
            continue
        for direction, target_name in room_config.get('exits', {}).items():
            target_room = rooms_by_name.get(target_name)
            if not target_room:
                continue
            existing_exits = [obj for obj in room.contents
                              if hasattr(obj, 'destination') and obj.destination == target_room]
            if not existing_exits:
                create_object(
                    'evennia.objects.objects.DefaultExit',
                    key=direction,
                    location=room,
                    destination=target_room,
                )
                print(f'    Created exit: {room_config["name"]} --{direction}--> {target_name}')

    # 3. Create NPCs
    for npc_config in config.get('npcs', []):
        npc_name = npc_config['name']
        npc_room_name = npc_config.get('room', '')
        npc_room = rooms_by_name.get(npc_room_name)
        if not npc_room:
            print(f'  WARNING: Room "{npc_room_name}" not found for NPC "{npc_name}"')
            continue

        # Find or create NPC
        existing_npcs = [o for o in npc_room.contents
                         if o.key.lower() == npc_name.lower()
                         and hasattr(o.db, 'topics')]
        if existing_npcs:
            npc = existing_npcs[0]
            print(f'  Updating NPC: {npc_name}')
        else:
            npc = create_object('typeclasses.npcs.ScenarioNPC', key=npc_name, location=npc_room)
            print(f'  Created NPC: {npc_name} in {npc_room_name}')

        # Set NPC attributes
        npc.db.npc_name = npc_name
        npc.db.examine_desc = npc_config.get('examine', '').strip()
        npc.db.desc = npc_name  # brief desc for room look

        # Build topics dict and unlocked list
        topics = {}
        unlocked = []

        for topic_config in npc_config.get('initial_topics', []):
            key = topic_config['topic']
            topics[key] = {
                'desc': topic_config.get('desc', ''),
                'type': topic_config.get('type', 'ask'),
                'response': topic_config.get('response', ''),
                'unlocks': topic_config.get('unlocks', []),
                'requires': topic_config.get('requires', ''),
                'sets_flag': topic_config.get('sets_flag', ''),
                'outcome_flag': topic_config.get('outcome_flag', ''),
            }
            unlocked.append(key)

        for topic_config in npc_config.get('unlockable_topics', []):
            key = topic_config['topic']
            topics[key] = {
                'desc': topic_config.get('desc', ''),
                'type': topic_config.get('type', 'ask'),
                'response': topic_config.get('response', ''),
                'unlocks': topic_config.get('unlocks', []),
                'requires': topic_config.get('requires', ''),
                'sets_flag': topic_config.get('sets_flag', ''),
                'outcome_flag': topic_config.get('outcome_flag', ''),
            }
            # NOT added to unlocked — must be unlocked via conversation

        npc.db.topics = topics
        npc.db.unlocked_topics = unlocked

    print(f'  Scenario "{scenario_name}" build complete.')


def build_all_scenarios():
    """Build all scenarios from YAML files in data/worlds/scenarios/."""
    scenarios_dir = os.path.abspath(SCENARIOS_DIR)
    if not os.path.isdir(scenarios_dir):
        print(f'No scenarios directory found at {scenarios_dir}')
        return

    yaml_files = sorted(f for f in os.listdir(scenarios_dir) if f.endswith('.yaml'))
    if not yaml_files:
        print('No scenario YAML files found')
        return

    print(f'Building {len(yaml_files)} scenario(s) from {scenarios_dir}')
    for filename in yaml_files:
        filepath = os.path.join(scenarios_dir, filename)
        with open(filepath) as f:
            config = yaml.safe_load(f)
        if config and 'name' in config:
            build_scenario(config)
        else:
            print(f'Skipping {filename} — missing "name" field')

    print('\nAll scenarios built.')
