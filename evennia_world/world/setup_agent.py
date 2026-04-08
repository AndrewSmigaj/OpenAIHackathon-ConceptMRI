"""
Create or update an agent account with Builder permissions.

Usage:
    cd evennia_world
    ../.venv/bin/python -c "
    import os, sys, django
    os.environ['DJANGO_SETTINGS_MODULE'] = 'server.conf.settings'
    sys.path.insert(0, os.getcwd())
    django.setup()
    import evennia; evennia._init()
    from world.setup_agent import setup_agent
    setup_agent()
    "

Reads EVENNIA_AGENT_USER and EVENNIA_AGENT_PASS from environment
(or .env file in project root). Idempotent — safe to re-run.
"""

import os

from evennia import create_object, search_object
from evennia.accounts.models import AccountDB


def setup_agent(username=None, password=None):
    """Create or find agent account + character, grant Builder permission."""
    username = username or os.environ.get("EVENNIA_AGENT_USER", "agent")
    password = password or os.environ.get("EVENNIA_AGENT_PASS")

    if not password:
        print("ERROR: No password. Set EVENNIA_AGENT_PASS env var.")
        return

    # Find or create account
    try:
        account = AccountDB.objects.get(username__iexact=username)
        print(f"Found existing account: {username} ({account.dbref})")
        account.set_password(password)
        account.save()
    except AccountDB.DoesNotExist:
        from evennia.accounts.accounts import DefaultAccount
        account = create_object(DefaultAccount, key=username)
        account.set_password(password)
        account.save()
        print(f"Created account: {username} ({account.dbref})")

    # Grant Builder permission
    if "Builder" not in account.permissions.all():
        account.permissions.add("Builder")
        print(f"  Granted Builder permission")
    else:
        print(f"  Already has Builder permission")

    # Find or create character
    chars = [c for c in account.characters if c.key.lower() == username.lower()]
    if chars:
        char = chars[0]
        print(f"Found existing character: {char.key} ({char.dbref})")
    else:
        char = create_object(
            "typeclasses.characters.Character",
            key=username,
        )
        account.puppet_object = char
        account.db._last_puppet = char
        char.db.account = account
        print(f"Created character: {char.key} ({char.dbref})")

    # Ensure character is somewhere (default: Hub #2)
    if not char.location:
        hub = search_object("#2")
        if hub:
            char.move_to(hub[0], quiet=True)
            print(f"  Moved {char.key} to Hub ({hub[0].dbref})")
        else:
            print(f"  WARNING: Hub (#2) not found, character has no location")

    print(f"\nAgent setup complete:")
    print(f"  Account: {username} ({account.dbref})")
    print(f"  Character: {char.key} ({char.dbref})")
    print(f"  Permissions: {list(account.permissions.all())}")
    print(f"  Location: {char.location}")
