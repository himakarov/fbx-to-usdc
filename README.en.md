# FBX to USDC Converter

[Русский](README.md) | [English](README.en.md)

Automates the manual pipeline of turning a character's FBX animation into a
self-contained `.usdc` (Houdini, Solaris). Builds the whole chain in one click:
FBX Character Import in SOPs → three nulls (rest / capture / animated) → SOP
Import UsdSkel Character in Solaris → USD ROP — and optionally writes the file
straight away.

It handles the common case where the mesh+skeleton and the animation live in
**two separate FBX files** on the same skeleton: both files are set on a single
FBX Character Import node (`fbxfile` + `animfbxfile`), which merges them itself —
no manual Bone Deform / Joint Deform.

## Install

1. Download the latest build from the [latest release](https://github.com/himakarov/fbx-to-usdc/releases/latest).
2. Find your Houdini user preferences folder and the `packages` folder inside it
(create `packages` if it doesn't exist yet):
  - Windows: `C:/Users/<name>/Documents/houdini22.0/packages/`
  - macOS: `~/Library/Preferences/houdini/22.0/packages/`
  - Linux: `~/houdini22.0/packages/` (use your version)
3. Unzip straight into `packages`, so you get:

```
houdini22.0/
└── packages/
    ├── fbx_to_usdc.json
    └── FbxToUsdcConverter/
        ├── VERSION
        ├── python/
        ├── config/
        └── scripts/
```

Nothing needs renaming — the archive is already laid out correctly.

4. Restart Houdini. A **CGA Tools** shelf appears with an **FBX>USDC** button.

## Usage

1. Click **FBX>USDC** on the shelf.
2. Set **Mesh FBX** — the mesh with its skeleton (rest). Provides rest geometry
and the capture pose.
3. Set **Animation FBX** — the clip on the same skeleton. Leave empty if the
mesh FBX already contains the animation.
4. The output `.usdc` path auto-fills from the animation FBX name (the per-shot
name); editable.
5. Set **FPS / Start / End**, or press **Use scene range**.
6. Leave **Write USDC now** off to only build and inspect the network, or tick
it to build and write in one pass.

The tool builds from scratch (variant A — unique node names each run):

```
/obj/<geo>
  fbxcharacterimport   (both files: fbxfile + animfbxfile)
    ├─ output 0 → REST_GEO       (Null)
    ├─ output 1 → CAPTURE_POSE   (Null)
    └─ output 2 → ANIMATED_POSE  (Null)

/stage
  usdskel_import   (animposepath / restgeopath / captureposepath)
        │
  usd_rop → <name>.usdc
```

## Save Style and the self-contained file

The USD ROP saves with **Flatten Stage (Collapse All Sublayers and
References)**. This matters: the `convert_to_agent` branch inside SOP Import
UsdSkel Character pulls a helper layer (`OUT_STATIC`) via a **reference**, so the
milder "Flatten Implicit Layers" doesn't fold it in and Houdini warns with
*"Layer saved to a location generated from a node path"*. A full stage flatten
collapses references too — the result is one portable `.usdc` with no external
layers.

Configurable in `config/settings.json` (`flatten_stage`, `usd_save_style`).

## Settings

`config/settings.json` holds node names, primitive paths, default fps/range, the
output path pattern and the save style. Edit it instead of the code. If it's
missing or broken, built-in defaults are used.

## Updating

The **Check for updates** button pulls the latest version from GitHub. If a
newer version exists, it's downloaded and overwrites the local files. Restart
Houdini after updating. The **Changelog** button shows what changed.
