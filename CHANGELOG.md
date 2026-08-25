# Changelog

## 1.1.1
- Removed a misleading fps warning. Both tabs used to warn that a clip would
  be "converted at" the FPS field's value when it differed from the source
  file - but checking an exported file shows the .usdc gets the clip's own
  timeCodesPerSecond (a 30fps clip exported with 24 in the field still comes
  out at 30, correct duration, nothing retimed). The reports now just state
  the source file's fps as information.

## 1.1.0
First feature release since 1.0.0. Everything from the 1.0.x line, summarised:

**Batch Convert tab**
- Convert many clips in one pass from a table of (mesh, animation, output)
  rows. "Add Pair..." for several different character+animation pairs;
  "Add Animations for One Mesh..." to pick a mesh once and multi-select many
  animation files.
- "Auto-detect range per row" detects each row's own frame range instead of
  applying one shared range to all, and flags rows whose source fps differs
  from the FPS field.
- Per-row report with the detected range, the written path, and per-row
  success/failure.

**Frame range handling**
- "Detect from Animation FBX" reads the clip's real frame range (from the
  clipinfo detail attribute, source_range x source_rate) - the clip's own
  frame numbers as authored, matching what the animator sees.
- "Shift animation to start at frame 0" retimes a clip that starts at an
  arbitrary frame, via a Time Shift SOP plus a custom clip range on the
  UsdSkel import.

**Stage assembly**
- Optional Reference node reading the written .usdc back into /stage.
- Optional chaining of those Reference nodes into one assembled stage.
- Optional cleanup of the per-clip build nodes once the file is written.
- New nodes are placed in their own free slot instead of stacking on top of
  earlier builds, and the reference chain stacks compactly.

**Export correctness**
- Subset Attributes (fbx_material_name) set on import, so the material tools
  have per-material GeomSubsets to assign onto.
- USD ROP saves with Flatten Stage, producing one self-contained .usdc.

**Reliability**
- Shelf registration moved to scripts/python/ready.py with hdefereval, fixing
  the button not appearing on startup on some builds.
- Self-update from GitHub with a Changelog viewer in the panel.

## 1.0.21
- Batch Convert with "Auto-detect range per row" now flags rows whose source
  file was authored at a different fps than the FPS field. Auto-detect only
  overrides Start/End - the shared FPS value is still applied to every row as
  entered, so a 30fps clip converted in a 24fps batch gets a per-row note in
  the report instead of being silently retimed.

## 1.0.20
- "Shift animation to start at frame 0" works end to end now. The Time Shift
  SOP fix in 1.0.19 was correct but had no visible effect, because SOP Import
  UsdSkel Character defaults to Clip Range = "Use clipinfo Detail Attribute",
  and clipinfo still carries the ORIGINAL source range (Time Shift does not
  rewrite it) - so the node kept importing the untouched source frames. With
  the shift enabled, the node is now switched to "Custom Frame Range"
  (cliprangemode='custom') with f1/f2 set to the retimed 0..(end-start).

## 1.0.19
- "Shift animation to start at frame 0" now actually shifts. The Time Shift
  SOP has no "shift" parm (the name assumed in 1.0.13-1.0.18, which produced
  a "Parm 'shift' not found" warning and no shift at all) - its parms are
  method/frame/time/... Correct approach: set method to By Frame and put the
  expression "$F + <start>" in "frame", because Time Shift pulls the frame
  named in that parm onto the current frame rather than offsetting by a
  constant.

## 1.0.18
- "Detect from Animation FBX" now reports the clip's own frame numbers -
  clipinfo's source_range x source_rate - instead of Houdini's
  retimed-into-scene-fps range x rate used in 1.0.17. For a 30fps clip in a
  24fps scene that is the difference between 235-563 (what the animator sees,
  verified against the same file in Cinema 4D) and 0-262 (Houdini's retimed
  version).
- The fps mismatch note now suggests setting the scene to the file's fps
  before converting, rather than describing the retime.

## 1.0.17
- "Detect from Animation FBX" now actually works. The node's Animation
  Start/End parms turned out to be unusable from Python - read
  programmatically they always report Houdini's scene $FSTART/$FEND (the
  generic 1-240), regardless of pressing Reload, cook(force=True) or
  requesting geometry() (the failed attempts in 1.0.14-1.0.16). The range is
  now read from the "clipinfo" detail attribute on the FBX import's animated
  output instead - the same source SOP Import UsdSkel Character uses for its
  "Use clipinfo Detail Attribute" Clip Range mode.
- Detect also fills FPS with the source file's native rate (clipinfo
  "source_rate"), and warns in the report when that differs from the scene
  fps - the detected range is in scene frames (Houdini retimes the clip on
  import), so a 30fps clip in a 24fps scene reports the retimed range, not
  the raw file frames.

## 1.0.16
- "Detect from Animation FBX" fix, take 2: confirmed the button parm name is
  "reload" (Import tab). detect_animation_range() now presses it and then
  forces a real cook via node.geometry() - node.cook(force=True) alone (used
  in 1.0.14/1.0.15) was not enough to make the node actually read the file
  before the Animation Start/End parms were read.

## 1.0.14
- Fixed: "Detect from Animation FBX" was reporting Houdini's generic scene
  range (1-240, i.e. $FSTART/$FEND) instead of the real file range. The
  temporary FBX Character Import node was never actually cooked before
  reading its Animation Start/End parms, so it had no file data to report -
  per the node's own tooltip, it falls back to the scene default when that
  happens. detect_animation_range() now forces a cook before reading the
  range.

## 1.0.13
- New: "Detect from Animation FBX" replaces "Use scene range" (Single tab).
  Reads the real frame range straight from the animation FBX (or the mesh FBX
  if no animation file is set) via a temporary, invisible FBX Character
  Import node - so a clip an animator sent starting at frame 90 is detected
  as 90-710 instead of defaulting to 1-240.
- New: "Shift animation to start at frame 0" (Single) / "Shift each row's
  animation to start at frame 0" (Batch) - retimes the animated stream (via a
  Time Shift SOP) so the written .usdc always starts at frame 0, regardless
  of what frame the source animation started at. The write range adjusts
  automatically (e.g. 90-710 becomes 0-620).
- New: "Auto-detect range per row" (Batch tab) - ignores the shared Start/End
  fields and detects each row's own animation range individually, so a batch
  of clips from different animators (each starting at a different frame) all
  convert correctly without manual entry.
- New public function core.detect_animation_range(fbx_path, anim_fbx_path).
- NOTE: the Time Shift amount uses the standard "shift" parm name, which
  hasn't been confirmed against a live node in this project (unlike the other
  parameters used elsewhere). If the exported animation doesn't start at
  frame 0 after enabling the shift option, or a warning about the "Time
  Shift amount" parm appears, check the parm's exact name on a Time Shift SOP
  and report it back.

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

## 1.0.5
- Added scripts/pythonrc.py as a second startup hook for shelf registration
  (more reliable than 456.py alone; idempotent, so no double buttons).
- SOP Import UsdSkel Character now sets Subset Attributes (restgeo_partitionattribs)
  to "fbx_material_name" by default, so the mesh is split into per-material
  GeomSubsets on import - required for Prop/Character Material Creator to have
  subsets to assign onto. Configurable via restgeo_partition_attribs in
  config/settings.json.

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
