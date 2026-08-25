# Changelog

## 1.0.12
- Reference chain nodes now stack with a tight, single-node spacing by
  default (reference_node_spacing in config/settings.json, default 1.2)
  instead of the wider spacing used for the build-node pairs - a chain of
  many clips (dozens of animations) now stays compact instead of stretching
  far down the network view.
- Fixed a UI alignment glitch: the "Chain onto the previous reference"
  checkbox (Single tab) was indented in a way that broke the row's alignment
  with the other checkboxes above/below it.

## 1.0.11
- Fixed: repeated builds (successive Single-tab presses, or Batch rows) no
  longer land on top of each other in /stage. Each build() call now looks at
  where existing nodes already sit and drops its new nodes into their own
  free vertical slot, instead of relying on layoutChildren()'s relative-only
  placement.
- New: "Chain onto the previous reference" (Single tab) / "Chain all rows
  into one assembled stage" (Batch tab) - wires each new Reference node's
  input to the previous one, so successive conversions build up a single
  composed stage (matching the common "several characters/animations laid
  out together" case) instead of N disconnected Reference nodes.
- New: "Clean up build nodes after export" (Single) / "...per row" (Batch) -
  once the .usdc is written (and referenced, if requested), deletes the
  per-clip build machinery (the OBJ FBX-import subnet and the UsdSkel-import
  + USD ROP nodes in /stage), leaving only the Reference node(s) behind so
  the network doesn't accumulate scratch nodes that are no longer needed.
- Reference nodes now live in their own column in /stage, separate from the
  per-clip build nodes, so the two groups read as distinct clusters.

## 1.0.10
- Fixed a broken package manifest: fbx_to_usdc.json had been accidentally
  overwritten with settings content during the v1.0.8 update, which made
  Houdini unable to locate the package at all (FBX2USDC_ROOT resolved to
  None) after updating via "Check for updates". Restored the correct
  manifest and the default_create_reference setting that was lost with it.

## 1.0.9
- Fixed: building/converting no longer rearranges the whole /stage network.
  stage.layoutChildren() with no arguments repositions every node in the
  network, scrambling any manual layout the user had; it's now scoped to only
  the nodes just created (layoutChildren(items=...)), so existing nodes stay
  exactly where they are.

## 1.0.8
- New: "Create Reference node" option (Single tab) - after writing the .usdc,
  optionally creates a Reference LOP in /stage reading the file back in,
  named after the animation clip, with Primitive Path /<name>. Off by default
  (default_create_reference in config/settings.json).
- New: "Batch Convert" tab - convert many clips in one pass via a table of
  (mesh, animation, output) rows. Covers both batch cases: several different
  character+animation pairs ("Add Pair..." - one call per pair, different mesh
  each time) and one character with many animations ("Add Animations for One
  Mesh..." - pick the mesh once, multi-select animation files, one row per
  file). Shared fps/range/write/reference settings apply to all rows; each row
  calls the same build() used by the Single tab. Report lists per-row
  success/failure and a final count.

## 1.0.7
- Fixed shelf button not appearing on startup: registration now runs from
  scripts/python/ready.py via hdefereval.executeDeferred (same pattern as the
  Character Material Tool), instead of scripts/456.py alone. 456.py runs too
  early on some builds (observed with Steam Houdini Indie) for shelf objects
  to be touched safely. 456.py is kept as a harmless secondary attempt.
- Removed scripts/pythonrc.py (unreliable, replaced by ready.py).

## 1.0.6
- Fixed Subset Attributes not applying: the restgeo_partitionattribs value has
  a separate enable toggle (restgeo_enablepartitionattribs) that must be set
  to 1, or the node ignores the text value. Now both are set on build.

## 1.0.5
- Added scripts/pythonrc.py as a second startup hook for shelf registration
  (more reliable than 456.py alone; idempotent, so no double buttons).
- SOP Import UsdSkel Character now sets Subset Attributes (restgeo_partitionattribs)
  to "fbx_material_name" by default, so the mesh is split into per-material
  GeomSubsets on import - required for Prop/Character Material Creator to have
  subsets to assign onto. Configurable via restgeo_partition_attribs in
  config/settings.json.

## 1.0.4
- New shelf icon.
- Added GitHub Actions release workflow: pushing a vX.Y.Z tag now auto-packages
  the repo and publishes the release, so the release zip always matches main.

## 1.0.3
- Self-update from GitHub (himakarov/fbx-to-usdc), same pattern as the Character
  Material Tool: "Check for updates" and "Changelog" buttons in the panel,
  stdlib-only updater (no git, no deps). Shows the installed version in the UI.
- Bilingual README (README.md RU / README.en.md EN) with a language switcher.
- Added .gitignore.

## 1.0.2
- USD ROP save style set to "flattenstage" (Flatten Stage: collapse all
  sublayers AND references) instead of flattenimplicitlayers. The agent
  OUT_STATIC layer inside convert_to_agent is pulled via a reference, which the
  implicit-only flatten preserved - so the "Layer saved to a location generated
  from a node path" message persisted. Full stage flatten folds it in, giving a
  truly self-contained .usdc and clearing the message.
- Settings: replaced flatten_implicit_layers with flatten_stage (default true)
  and usd_save_style (default "flattenstage").

## 1.0.1
- USD ROP now flattens implicit sublayers into the single output .usdc
  (flattenimplicitlayers). Removes the "Layer saved to a location generated
  from a node path" warning caused by the convert_to_agent/OUT_STATIC.usd
  implicit layer, giving one self-contained, portable file.
- Node-type resolver: SOP Import UsdSkel Character now found as
  kinefx::sopcharacterimport (was looking only under labs::).
- New setting: flatten_implicit_layers (default true).

## 1.0.0
- First release. Single-shot mode with a PySide panel.
- Two file inputs: Mesh FBX (fbxfile) + Animation FBX (animfbxfile) - both set
  on one FBX Character Import node, which merges them internally (same
  skeleton). No Bone Deform / Joint Deform needed.
- Builds from scratch (variant A): /obj geo with FBX Character Import + three
  output nulls REST_GEO / CAPTURE_POSE / ANIMATED_POSE (outputs 0/1/2) ->
  Solaris SOP Import UsdSkel Character (animposepath / restgeopath /
  captureposepath) -> USD ROP.
- "Write USDC now" flag: off = build network only, on = build and write .usdc.
- FPS / Start / End fields, with a "Use scene range" button.
- Output name auto-fills from the animation FBX (per-shot name).
- Node types resolved against the install (Labs / SideFX name fallbacks).
- Settings in config/settings.json; built-in defaults if it is missing.
