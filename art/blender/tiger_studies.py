"""Tiger studies: the tiger built with every technique in studies.py.

    blender --background --factory-startup --python art/blender/tiger_studies.py -- <output folder> [names]
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "zoo"))

import studies  # noqa: E402
from tiger import Tiger  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
studies.build_all(Tiger(), os.path.abspath(args[0] if args else "art/studies/tiger"), args[1:])
