import glob
import os
from dataclasses import dataclass
from typing import List

_BROCHURES_DIR = "brochures"


@dataclass
class Brochure:
    key: str
    label: str
    path: str


def list_brochures() -> List[Brochure]:
    paths = sorted(glob.glob(os.path.join(_BROCHURES_DIR, "*.pdf")))
    brochures = []
    for path in paths:
        stem = os.path.splitext(os.path.basename(path))[0]
        brochures.append(Brochure(key=stem, label=stem.replace("_", " "), path=path))
    return brochures
