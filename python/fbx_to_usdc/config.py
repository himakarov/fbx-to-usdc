"""
config.py - loads settings.json for the FBX -> USDC Converter.

Everything project-specific (default fps, node-name prefixes, primitive paths,
the USD ROP save-style) lives in settings.json so tweaking behaviour never
requires touching code. If the file is missing or broken we fall back to sane
built-in defaults, so the tool never hard-crashes on a bad edit.

Public surface:
    load_config(path=None) -> (Config, warning_or_None)
"""

import os
import json


_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DEFAULT_JSON = os.path.join(_PKG_ROOT, "config", "settings.json")

# Fallback to a copy next to this module, if one exists.
if not os.path.isfile(_DEFAULT_JSON):
    _local = os.path.join(os.path.dirname(__file__), "settings.json")
    if os.path.isfile(_local):
        _DEFAULT_JSON = _local


# Built-in defaults - used when settings.json is absent or unreadable. These
# mirror the shipped settings.json so the tool is fully functional even with no
# config file at all.
_BUILTIN = {
    # network layout
    "obj_subnet_name": "fbx2usdc_import",
    "fbx_import_node": "kinefx::fbxcharacterimport",
    "null_rest": "REST_GEO",
    "null_capture": "CAPTURE_POSE",
    "null_animated": "ANIMATED_POSE",
    "usdskel_import_node": "kinefx::sopcharacterimport",
    "usd_rop_node": "usd_rop",

    # UsdSkel import defaults
    "skeleton_primitive_path": "skeleton",
    "animation_primitive_path": "animation",

    # frame / fps defaults (used when the FBX carries no usable range)
    "default_fps": 24,
    "default_start": 1,
    "default_end": 240,

    # output
    "usdc_output_pattern": "$HIP/usd/{name}.usdc",
    "default_write_now": False,

    # USD output: flatten the whole stage (collapse sublayers AND
    # references) into one self-contained .usdc. flattenstage is what clears
    # the auto-generated-path message from the agent OUT_STATIC reference.
    "flatten_stage": True,
    "usd_save_style": "flattenstage",

    # Import Rest Geometry Data > Subset Attributes: SOP attribute used to
    # split the mesh into per-material GeomSubsets on import. Needed so the
    # material tools (Prop/Character Material Creator) have subsets to assign
    # onto.
    "restgeo_partition_attribs": "fbx_material_name",

    # Single tab: create a Reference LOP reading the written .usdc back into
    # /stage by default.
    "default_create_reference": False,

    # Vertical spacing between chained/stacked Reference nodes in /stage.
    # Kept tight by default so a chain of many clips (dozens) stays compact.
    "reference_node_spacing": 1.2,
}


class Config(object):
    def __init__(self, data):
        merged = dict(_BUILTIN)
        merged.update(data or {})
        self._data = merged

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __getitem__(self, key):
        return self._data[key]

    def as_dict(self):
        return dict(self._data)


def load_config(path=None):
    """Load settings.json. Returns (Config, warning). On any failure the
    Config is still valid (built-in defaults) and the warning describes what
    went wrong so the UI can surface it without blocking the build."""
    target = path or _DEFAULT_JSON
    if not os.path.isfile(target):
        # no file at all is fine - pure built-in defaults, no warning needed
        return Config({}), None
    try:
        with open(target, "r") as f:
            data = json.load(f)
        return Config(data), None
    except Exception as exc:
        return Config({}), "Using built-in defaults (%s failed: %s)" % (
            os.path.basename(target), exc)
