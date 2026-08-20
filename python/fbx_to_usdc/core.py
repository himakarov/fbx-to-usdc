"""
core.py - build logic for the FBX -> USDC Converter.

The real pipeline (confirmed against the working scene), and what this builds:

  SOP context (/obj/geo1-style geo):
    FBX Character Import (kinefx::fbxcharacterimport) reads BOTH files itself:
        fbxfile     = the mesh + skeleton (rest)   e.g. INS_A_Cin_SKM.fbx
        animfbxfile = the animation clip           e.g. char_..._shot0010.fbx
    The node does the mesh<->animation merge internally (same skeleton), so no
    Bone Deform / Joint Deform is needed. Its three outputs are tapped by nulls:
        output 0 -> REST_GEO       (Null)
        output 1 -> CAPTURE_POSE   (Null)
        output 2 -> ANIMATED_POSE  (Null)

  LOP context (/stage):
    SOP Import UsdSkel Character (labs::sopcharacterimport) reads the three SOP
    paths and assembles a UsdSkel hierarchy:
        animposepath    = .../ANIMATED_POSE
        restgeopath     = .../REST_GEO
        captureposepath = .../CAPTURE_POSE

    A USD ROP then writes the composed stage to a single .usdc.

Design (v1): VARIANT A - build the whole chain from scratch every run under
unique node names. No reuse. Predictable, easy to debug.

UI-independent; called from ui.py. The one public entry is build().
"""

import os
import hou

from . import config as _config


# ---------------------------------------------------------------------------
# Node-type resolution (robust across Houdini builds / Labs vs SideFX)
# ---------------------------------------------------------------------------
_FBX_IMPORT_CANDIDATES = (
    "kinefx::fbxcharacterimport",
    "kinefx::fbxcharacterimport::2.0",
    "labs::fbxcharacterimport",
    "fbxcharacterimport",
)

_USDSKEL_IMPORT_CANDIDATES = (
    "kinefx::sopcharacterimport",
    "labs::sopcharacterimport",
    "sopcharacterimport",
)

_REFERENCE_CANDIDATES = (
    "reference",
)


def _resolve_sop_type(candidates):
    table = hou.sopNodeTypeCategory().nodeTypes()
    for name in candidates:
        if name in table:
            return name
    return None


def _resolve_lop_type(candidates):
    table = hou.lopNodeTypeCategory().nodeTypes()
    for name in candidates:
        if name in table:
            return name
    return None


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _unique_name(parent, base):
    """A child name unique under `parent`: base, base_1, base_2, ..."""
    existing = set(c.name() for c in parent.children())
    if base not in existing:
        return base
    i = 1
    while "%s_%d" % (base, i) in existing:
        i += 1
    return "%s_%d" % (base, i)


def _clean_name(path):
    """Filesystem/USD-friendly stem from a file path: /a/b/Char_Run.fbx ->
    'Char_Run'."""
    stem = os.path.splitext(os.path.basename(path))[0]
    safe = "".join(ch if (ch.isalnum() or ch in "_-") else "_" for ch in stem)
    return safe or "character"


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build(fbx_path,
          anim_fbx_path,
          usdc_path,
          fps=None,
          start=None,
          end=None,
          write_now=False,
          create_reference=False,
          cfg=None):
    """Build the FBX -> UsdSkel -> USDC chain from scratch.

    Args:
        fbx_path:       absolute path to the mesh+skeleton .fbx (fbxfile)
        anim_fbx_path:  absolute path to the animation .fbx (animfbxfile).
                        May be empty if the mesh file already carries the anim.
        usdc_path:      output .usdc path (may contain $HIP etc.)
        fps:            frames per second (int) or None -> config default
        start,end:      frame range (ints) or None -> config defaults
        write_now:      if True, execute the USD ROP and write the .usdc now
        create_reference: if True (and the file was actually written), also
                        create a standalone Reference LOP in /stage that reads
                        the written .usdc back in, named after the animation
                        clip. Useful for immediately dropping the exported
                        character into the same scene (e.g. to lay out a shot).
        cfg:            a config.Config; loaded if None

    Returns a dict report (see ui._report_result), or {"error": ...}.
    """
    warnings = []
    if cfg is None:
        cfg, cfg_warn = _config.load_config()
        if cfg_warn:
            warnings.append(cfg_warn)

    # --- validate input --------------------------------------------------
    expanded_fbx = hou.text.expandString(fbx_path) if fbx_path else ""
    if not expanded_fbx:
        return {"error": "No mesh FBX file given."}
    if not os.path.isfile(expanded_fbx):
        return {"error": "Mesh FBX does not exist:\n%s" % expanded_fbx}

    expanded_anim = hou.text.expandString(anim_fbx_path) if anim_fbx_path else ""
    if anim_fbx_path and not os.path.isfile(expanded_anim):
        return {"error": "Animation FBX does not exist:\n%s" % expanded_anim}

    if not usdc_path:
        return {"error": "No output .usdc path given."}

    fbx_type = _resolve_sop_type(_FBX_IMPORT_CANDIDATES)
    if fbx_type is None:
        return {"error": "FBX Character Import node type not found (looked "
                         "for: %s)." % ", ".join(_FBX_IMPORT_CANDIDATES)}

    usdskel_type = _resolve_lop_type(_USDSKEL_IMPORT_CANDIDATES)
    if usdskel_type is None:
        return {"error": "SOP Import UsdSkel Character (LOP) node type not "
                         "found (looked for: %s)."
                         % ", ".join(_USDSKEL_IMPORT_CANDIDATES)}

    # name the network / default output after the animation clip when present
    # (that's usually the meaningful per-shot name), else the mesh file.
    name = _clean_name(expanded_anim) if expanded_anim else _clean_name(expanded_fbx)

    if start is None:
        start = int(cfg.get("default_start", 1))
    if end is None:
        end = int(cfg.get("default_end", 240))
    if fps is None:
        fps = int(cfg.get("default_fps", 24))

    report = {"warnings": warnings, "written": False, "usdc": usdc_path}

    # ================================================================
    # 1. SOP context: geo container + FBX Character Import + 3 nulls
    # ================================================================
    obj = hou.node("/obj")
    geo_name = _unique_name(obj, "%s_%s" % (cfg.get("obj_subnet_name",
                                                    "fbx2usdc_import"), name))
    geo = obj.createNode("geo", geo_name)
    report["obj_subnet"] = geo.path()

    fbx_node = geo.createNode(fbx_type, "fbxcharacterimport")
    # both file parms live on this one node
    _set_parm(fbx_node, "fbxfile", expanded_fbx, warnings, "FBX File")
    if expanded_anim:
        _set_parm(fbx_node, "animfbxfile", expanded_anim, warnings,
                  "Animation FBX File")

    report["fbx_node"] = fbx_node.path()

    # three nulls, tapping the confirmed output order:
    #   0 = rest geo, 1 = capture pose, 2 = animated pose
    null_specs = (
        ("rest", cfg.get("null_rest", "REST_GEO"), 0),
        ("capture", cfg.get("null_capture", "CAPTURE_POSE"), 1),
        ("animated", cfg.get("null_animated", "ANIMATED_POSE"), 2),
    )
    nulls = {}
    for key, null_name, out_idx in null_specs:
        n = geo.createNode("null", null_name)
        try:
            n.setInput(0, fbx_node, out_idx)
        except Exception as exc:
            warnings.append("Could not wire %s null to output %d: %s"
                            % (key, out_idx, exc))
        nulls[key] = n

    report["nulls"] = {k: v.path() for k, v in nulls.items()}
    geo.layoutChildren()

    # ================================================================
    # 2. LOP context: SOP Import UsdSkel Character
    # ================================================================
    stage = hou.node("/stage")
    usdskel = stage.createNode(usdskel_type,
                               _unique_name(stage, "usdskel_import_%s" % name))
    report["usdskel_node"] = usdskel.path()

    # confirmed parm names on this node
    _set_parm(usdskel, "animposepath", nulls["animated"].path(),
              warnings, "Animated Pose path")
    _set_parm(usdskel, "restgeopath", nulls["rest"].path(),
              warnings, "Rest Geometry path")
    _set_parm(usdskel, "captureposepath", nulls["capture"].path(),
              warnings, "Capture Pose path")

    # fps + primitive paths (optional parms; quiet if absent)
    _set_parm(usdskel, "fps", fps, warnings, "fps", quiet=True)
    _set_parm(usdskel, "skeletonprimpath",
              cfg.get("skeleton_primitive_path", "skeleton"),
              warnings, "skeleton prim path", quiet=True)
    _set_parm(usdskel, "animationprimpath",
              cfg.get("animation_primitive_path", "animation"),
              warnings, "animation prim path", quiet=True)

    # Subset Attributes (Import Rest Geometry Data block): split the mesh into
    # GeomSubsets by this SOP attribute, so the material tools (Prop/Character
    # Material Creator) have per-material subsets to assign onto. This has a
    # separate enable toggle (restgeo_enablepartitionattribs) that must be
    # switched on, or the text value alone is ignored by the node.
    _set_parm(usdskel, "restgeo_enablepartitionattribs", 1,
              warnings, "Subset Attributes toggle (rest geometry)", quiet=True)
    _set_parm(usdskel, "restgeo_partitionattribs",
              cfg.get("restgeo_partition_attribs", "fbx_material_name"),
              warnings, "Subset Attributes (rest geometry)", quiet=True)

    # ================================================================
    # 3. USD ROP writing the composed stage to .usdc
    # ================================================================
    rop = stage.createNode("usd_rop",
                           _unique_name(stage, "%s_%s"
                                        % (cfg.get("usd_rop_node", "usd_rop"),
                                           name)))
    rop.setInput(0, usdskel)
    _set_first_parm(rop, ("lopoutput", "outputfile"), usdc_path,
                    warnings, "USD output path")
    _set_first_parm(rop, ("fileperframe",), 0, warnings, "file-per-frame",
                    quiet=True)
    # Save Style = "Flatten Stage (Collapse All Sublayers and References)".
    # The convert_to_agent branch inside SOP Import UsdSkel Character pulls its
    # OUT_STATIC layer via a REFERENCE, so the milder "flattenimplicitlayers"
    # (which preserves references) left it as an external layer with an
    # auto-generated path - hence the "Layer saved to a location generated from
    # a node path" message. "flattenstage" collapses references too, folding
    # everything into one self-contained .usdc and clearing the message.
    flatten_style = (cfg.get("usd_save_style", "flattenstage")
                     if cfg.get("flatten_stage", True) else "separate")
    _set_first_parm(rop, ("savestyle",), flatten_style,
                    warnings, "save style", quiet=True)
    _set_range_parms(rop, start, end, warnings, trange_full=True)
    report["rop"] = rop.path()

    # Lay out only the nodes we just created (items=...), not the whole
    # network - layoutChildren() with no arguments repositions EVERY node in
    # /stage, which would scramble any manual arrangement the user already
    # has in the network view.
    try:
        stage.layoutChildren(items=(usdskel, rop))
    except Exception:
        pass

    # ================================================================
    # 4. optionally write now
    # ================================================================
    if write_now:
        out_dir = os.path.dirname(hou.text.expandString(usdc_path))
        if out_dir and not os.path.isdir(out_dir):
            try:
                os.makedirs(out_dir)
            except Exception as exc:
                warnings.append("Could not create output folder %s: %s"
                                % (out_dir, exc))
        try:
            rop.parm("execute").pressButton()
            report["written"] = True
            report["usdc"] = hou.text.expandString(usdc_path)
        except Exception as exc:
            warnings.append("Write failed: %s" % exc)

    # ================================================================
    # 5. optionally create a Reference LOP reading the written file back in
    # ================================================================
    if create_reference:
        if not report.get("written"):
            warnings.append("Reference node skipped: USDC was not written "
                            "(enable 'Write USDC now' to create it).")
        else:
            ref_type = _resolve_lop_type(_REFERENCE_CANDIDATES)
            if ref_type is None:
                warnings.append("Reference node type not found (looked for: "
                                "%s)." % ", ".join(_REFERENCE_CANDIDATES))
            else:
                ref_node = stage.createNode(
                    ref_type, _unique_name(stage, name))
                _set_first_parm(ref_node, ("primpath1", "primpath"),
                                "/" + name, warnings, "Reference primitive path")
                _set_first_parm(ref_node, ("filepath1", "filepath"),
                                report["usdc"], warnings,
                                "Reference file pattern")
                report["reference_node"] = ref_node.path()
                try:
                    stage.layoutChildren(items=(ref_node,))
                except Exception:
                    pass

    return report


# ---------------------------------------------------------------------------
# Parm-setting helpers
# ---------------------------------------------------------------------------
def _set_parm(node, parm_name, value, warnings, label, quiet=False):
    """Set a single parm by exact name. Warn if missing (unless quiet)."""
    p = node.parm(parm_name)
    if p is None:
        if not quiet:
            warnings.append("Parm '%s' for %s not found on %s."
                            % (parm_name, label, node.path()))
        return False
    try:
        p.set(value)
        return True
    except Exception as exc:
        warnings.append("Could not set %s (%s): %s" % (label, parm_name, exc))
        return False


def _set_first_parm(node, parm_names, value, warnings, label, quiet=False):
    """Set the first parm in parm_names that exists (names vary by ROP build)."""
    for pn in parm_names:
        p = node.parm(pn)
        if p is not None:
            try:
                p.set(value)
                return True
            except Exception as exc:
                warnings.append("Could not set %s (%s): %s" % (label, pn, exc))
                return False
    if not quiet:
        warnings.append("Parm for %s not found on %s (tried: %s)."
                        % (label, node.path(), ", ".join(parm_names)))
    return False


def _set_range_parms(node, start, end, warnings, trange_full=False):
    """Set a frame range via the standard f1/f2 parms; flip trange on ROPs."""
    if trange_full:
        tr = node.parm("trange")
        if tr is not None:
            try:
                tr.set(1)  # Render Frame Range
            except Exception:
                pass
    for pn, val in (("f1", start), ("f2", end)):
        p = node.parm(pn)
        if p is not None:
            try:
                p.deleteAllKeyframes()
                p.set(val)
            except Exception as exc:
                warnings.append("Could not set %s: %s" % (pn, exc))
