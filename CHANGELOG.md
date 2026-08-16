# Changelog

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
