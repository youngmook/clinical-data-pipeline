# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from .client import PubChemClient, PubChemError
from .classification_nodes import (
    PubChemClassificationClient,
    PubChemClassificationError,
)
from .pug_view import (
    PubChemPugViewClient,
    PubChemPugViewError,
)
from .web_fallback import (
    PubChemWebFallbackClient,
    PubChemWebFallbackError,
)

__all__ = [
    # Core PUG REST client
    "PubChemClient",
    "PubChemError",

    # Classification Nodes (HNID → CID)
    "PubChemClassificationClient",
    "PubChemClassificationError",

    # PUG-View annotations (CID → NCT IDs)
    "PubChemPugViewClient",
    "PubChemPugViewError",
    # Web page fallback
    "PubChemWebFallbackClient",
    "PubChemWebFallbackError",
]
