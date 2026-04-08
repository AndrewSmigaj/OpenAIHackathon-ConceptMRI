"""
Parse Harmony channels from model output.

gpt-oss-20b uses the Harmony response format with special token delimiters:
  <|channel|>name<|message|>content<|end|>     (non-final channels)
  <|channel|>name<|message|>content<|return|>   (final channel / EOS)

The 'analysis' channel contains chain-of-thought reasoning.
The 'final' channel contains the user-facing response (mapped to 'action').
"""

import re
import logging

logger = logging.getLogger(__name__)

# Matches: <|channel|>name<|message|>content<|end|> or <|return|>
# Non-greedy content match; re.DOTALL lets content span newlines.
_HARMONY_CHANNEL_RE = re.compile(
    r'<\|channel\|>(\w+)<\|message\|>(.*?)(?:<\|end\|>|<\|return\|>|\Z)',
    re.DOTALL,
)


def parse_harmony_channels(text: str) -> dict:
    """Extract Harmony channels from model output.

    Parses <|channel|>name<|message|>content<|end|> patterns from decoded text
    (must be decoded with skip_special_tokens=False).

    Maps 'analysis' channel → analysis, 'final' channel → action.
    Returns {"analysis": str, "action": str, "raw": str}.
    If no channels found, strips Harmony tokens and treats as action (fallback).
    """
    raw = text
    channels = {}
    for match in _HARMONY_CHANNEL_RE.finditer(text):
        channel_name = match.group(1)
        channel_content = match.group(2).strip()
        channels[channel_name] = channel_content

    analysis = channels.get("analysis", "")
    action = channels.get("final", "")

    if not analysis and not action:
        logger.warning("No Harmony channels found in output — treating entire output as action")
        cleaned = re.sub(r'<\|(?:channel|message|end|start|return)\|>', '', text).strip()
        action = cleaned

    return {"analysis": analysis, "action": action, "raw": raw}
