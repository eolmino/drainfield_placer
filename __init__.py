"""
Drainfield Placer - Automatic Drainfield Configuration and Placement
"""

from .config_loader import ConfigLoader
from .selector import DrainFieldSelector
from .geometry import parse_user_boundary, validate_boundary
from .placer import (
    place_drainfield,
    place_split_drainfield,
    create_placement_summary
)

__version__ = '1.0.0'
__all__ = [
    'ConfigLoader',
    'DrainFieldSelector',
    'parse_user_boundary',
    'validate_boundary',
    'place_drainfield',
    'place_split_drainfield',
    'create_placement_summary'
]
