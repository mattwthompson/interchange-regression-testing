import re
from pathlib import Path
from typing import Any, Dict, OrderedDict

import openmm
import xmltodict

_INDEX_REGEX = re.compile(r"^p\d+$")


def openmm_system_xml_postprocessor(_, key, value):

    if key.startswith("@"):
        key = key[1:]  # Drop the @ prefix for attributes.

    try:
        # Try to guess the numeric type of number looking values
        value = int(value) if "." not in value else float(value)
    except (ValueError, TypeError):
        pass

    if isinstance(value, OrderedDict):
        value = dict(value)
    if isinstance(value, dict) and len(value) == 1 and key[:-1] in value:
        # Un-nest things Like Constraints: {Constraint: [...]}} to Constraints: [...]
        # and ensure the inner value is a list.
        value = value[key[:-1]]
        value = value if isinstance(value, list) else [value]

    if isinstance(value, list) and len(value) > 0:

        first_item = value[0]
        index_keys = [k for k in first_item if re.match(_INDEX_REGEX, k) is not None]

        # We should **only** sort lists where it looks like the items have an index to
        # a particle i.e. a pXXX attribute, e.g. Constraints but not Particles.
        should_sort = len(index_keys) > 0 and all(
            f"p{i + 1}" in index_keys for i in range(len(index_keys))
        )

        item_keys = sorted(first_item)

        if should_sort:
            value = sorted(value, key=lambda v: tuple(v[k] for k in item_keys))

    if key == "Forces":

        # Sort the forces into a most likely deterministic order.
        assert len({(v["type"], v["name"]) for v in value}) == len(value)
        value = sorted(value, key=lambda v: (v["type"], v["name"]))

    return key, value


def openmm_system_to_dict(system: openmm.System) -> Dict[str, Any]:

    system_dict = xmltodict.parse(
        openmm.XmlSerializer.serialize(system),
        postprocessor=openmm_system_xml_postprocessor,
    )["System"]

    return system_dict


def load_openmm_system_as_dict(path: Path) -> Dict[str, Any]:

    with path.open("r") as file:

        system_dict = xmltodict.parse(
            file.read(), postprocessor=openmm_system_xml_postprocessor
        )["System"]

    return system_dict
