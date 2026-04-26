"""
Fixed layer windows for clustering schemas.

A **window** is a 6-layer range. A **transition** is a 2-layer pair within a
window (showing before-cluster, after-cluster, and the routes between them).
Six transitions per window, four windows total.

Mirrored on the frontend in `frontend/src/constants/layerRanges.ts`. Values are
simple enough that drift risk is low; if you change one side, change both.
"""

LAYER_WINDOWS = [
    {
        "id": "w0",
        "label": "Layers 0-5",
        "layers": [0, 5],
        "transitions": [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6]],
    },
    {
        "id": "w1",
        "label": "Layers 5-11",
        "layers": [5, 11],
        "transitions": [[5, 6], [6, 7], [7, 8], [8, 9], [9, 10], [10, 11]],
    },
    {
        "id": "w2",
        "label": "Layers 11-17",
        "layers": [11, 17],
        "transitions": [[11, 12], [12, 13], [13, 14], [14, 15], [15, 16], [16, 17]],
    },
    {
        "id": "w3",
        "label": "Layers 17-23",
        "layers": [17, 23],
        "transitions": [[17, 18], [18, 19], [19, 20], [20, 21], [21, 22], [22, 23]],
    },
]


def window_id_for_transition(transition_layers: list[int]) -> str:
    """Return the window id whose `transitions` list contains the given pair.

    For boundary transitions present in two windows (e.g. [5,6] is in both w0
    and w1), the earlier window wins — first match in LAYER_WINDOWS order.
    Raises ValueError if no window contains the transition.
    """
    for window in LAYER_WINDOWS:
        for t in window["transitions"]:
            if t == transition_layers:
                return window["id"]
    raise ValueError(f"No window contains transition {transition_layers}")
