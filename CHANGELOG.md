# Changelog

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
