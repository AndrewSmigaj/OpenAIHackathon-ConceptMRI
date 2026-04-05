"""
Parse harmony channels from model output.

Extracts <analysis> and <action> tagged content using simple string matching.
If tags are missing or malformed, treats the entire output as the action channel.
"""

import logging

logger = logging.getLogger(__name__)


def parse_harmony_channels(text: str) -> dict:
    """Extract <analysis> and <action> from model output.

    Uses simple string matching (str.find), not regex.
    Returns {"analysis": str, "action": str, "raw": str}
    If tags missing: entire output is action, logged as warning.
    """
    raw = text
    analysis = ""
    action = ""

    # Extract analysis channel
    a_start = text.find("<analysis>")
    a_end = text.find("</analysis>")
    if a_start != -1 and a_end != -1 and a_end > a_start:
        analysis = text[a_start + len("<analysis>"):a_end].strip()
    elif a_start != -1 or a_end != -1:
        logger.warning("Malformed <analysis> tags in model output")

    # Extract action channel
    act_start = text.find("<action>")
    act_end = text.find("</action>")
    if act_start != -1 and act_end != -1 and act_end > act_start:
        action = text[act_start + len("<action>"):act_end].strip()
    elif act_start != -1 or act_end != -1:
        logger.warning("Malformed <action> tags in model output")

    # Fallback: if no valid tags found, treat entire output as action
    if not analysis and not action:
        logger.warning("No harmony channel tags found — treating entire output as action")
        action = text.strip()

    return {"analysis": analysis, "action": action, "raw": raw}
