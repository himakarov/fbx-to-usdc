"""
ui.py - PySide dialog for the FBX -> USDC Converter.

Pick the mesh FBX and the animation FBX, pick where the .usdc goes, set fps /
frame range, choose whether to write immediately, press Build. The tool
assembles the SOP FBX Character Import (both files on one node) -> three nulls
(rest / capture / animated) -> Solaris SOP Import UsdSkel Character -> USD ROP
from scratch (variant A), and optionally writes the .usdc.

Launched from the CGA Tools shelf via:
    from fbx_to_usdc import ui
    ui.show()
"""

import os
import hou

try:
    from PySide6 import QtWidgets
except ImportError:
    from PySide2 import QtWidgets

from . import core
from . import config as _config


def _exec_dialog(d):
    """PySide6 uses exec(); PySide2 uses exec_(). Support both."""
    fn = getattr(d, "exec", None) or getattr(d, "exec_")
    return fn()


_dialog = None  # keep a reference so the window is not garbage-collected


class FbxToUsdcDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(FbxToUsdcDialog, self).__init__(parent)
        self.setWindowTitle("FBX to USDC Converter")
        self.setMinimumWidth(580)
        self.setMinimumHeight(470)
        self._cfg, cfg_warn = _config.load_config()
        self._build_ui()
        if cfg_warn:
            self._say(cfg_warn)

    # -- construction -------------------------------------------------------
    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 1. mesh FBX
        mesh_label = QtWidgets.QLabel("Mesh FBX (skeleton + skin, rest)")
        mesh_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(mesh_label)

        hint = QtWidgets.QLabel(
            "The character mesh with its skeleton. Provides rest geometry and "
            "the capture pose.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #999;")
        layout.addWidget(hint)

        mesh_row = QtWidgets.QHBoxLayout()
        self.fbx_edit = QtWidgets.QLineEdit()
        self.fbx_edit.setPlaceholderText("$HIP/models/characters/.../char_SKM.fbx")
        mesh_browse = QtWidgets.QPushButton("...")
        mesh_browse.setMaximumWidth(36)
        mesh_browse.clicked.connect(self._browse_fbx)
        mesh_row.addWidget(self.fbx_edit, stretch=1)
        mesh_row.addWidget(mesh_browse)
        layout.addLayout(mesh_row)

        # 2. animation FBX
        anim_label = QtWidgets.QLabel("Animation FBX (same skeleton)")
        anim_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(anim_label)

        anim_hint = QtWidgets.QLabel(
            "The animation clip on the same skeleton. The FBX Character Import "
            "node merges it with the mesh. Leave empty if the mesh FBX already "
            "contains the animation.")
        anim_hint.setWordWrap(True)
        anim_hint.setStyleSheet("color: #999;")
        layout.addWidget(anim_hint)

        anim_row = QtWidgets.QHBoxLayout()
        self.anim_edit = QtWidgets.QLineEdit()
        self.anim_edit.setPlaceholderText("$HIP/animations/.../char_anim_shot0010.fbx")
        self.anim_edit.editingFinished.connect(self._maybe_fill_output)
        anim_browse = QtWidgets.QPushButton("...")
        anim_browse.setMaximumWidth(36)
        anim_browse.clicked.connect(self._browse_anim)
        anim_row.addWidget(self.anim_edit, stretch=1)
        anim_row.addWidget(anim_browse)
        layout.addLayout(anim_row)

        # 3. USDC output
        out_label = QtWidgets.QLabel("Output .usdc")
        out_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(out_label)

        out_row = QtWidgets.QHBoxLayout()
        self.out_edit = QtWidgets.QLineEdit()
        self.out_edit.setPlaceholderText(
            self._cfg.get("usdc_output_pattern", "$HIP/usd/{name}.usdc"))
        out_browse = QtWidgets.QPushButton("...")
        out_browse.setMaximumWidth(36)
        out_browse.clicked.connect(self._browse_output)
        out_row.addWidget(self.out_edit, stretch=1)
        out_row.addWidget(out_browse)
        layout.addLayout(out_row)

        # 4. fps + frame range
        range_row = QtWidgets.QHBoxLayout()

        range_row.addWidget(QtWidgets.QLabel("FPS"))
        self.fps_spin = QtWidgets.QSpinBox()
        self.fps_spin.setRange(1, 240)
        self.fps_spin.setValue(int(self._cfg.get("default_fps", 24)))
        range_row.addWidget(self.fps_spin)

        range_row.addSpacing(16)
        range_row.addWidget(QtWidgets.QLabel("Start"))
        self.start_spin = QtWidgets.QSpinBox()
        self.start_spin.setRange(-100000, 100000)
        self.start_spin.setValue(int(self._cfg.get("default_start", 1)))
        range_row.addWidget(self.start_spin)

        range_row.addWidget(QtWidgets.QLabel("End"))
        self.end_spin = QtWidgets.QSpinBox()
        self.end_spin.setRange(-100000, 100000)
        self.end_spin.setValue(int(self._cfg.get("default_end", 240)))
        range_row.addWidget(self.end_spin)

        range_row.addStretch(1)
        self.scene_btn = QtWidgets.QPushButton("Use scene range")
        self.scene_btn.clicked.connect(self._use_scene_range)
        range_row.addWidget(self.scene_btn)
        layout.addLayout(range_row)

        # 5. write-now flag
        self.write_check = QtWidgets.QCheckBox(
            "Write USDC now (unchecked = only build the network)")
        self.write_check.setChecked(bool(self._cfg.get("default_write_now", False)))
        layout.addWidget(self.write_check)

        # 6. build + report
        self.build_btn = QtWidgets.QPushButton("Build && Convert")
        self.build_btn.setMinimumHeight(34)
        self.build_btn.clicked.connect(self._on_build)
        layout.addWidget(self.build_btn)

        # 7. maintenance row: updates + changelog
        maint_row = QtWidgets.QHBoxLayout()
        self.update_btn = QtWidgets.QPushButton("Check for updates")
        self.update_btn.clicked.connect(self._on_check_updates)
        self.changelog_btn = QtWidgets.QPushButton("Changelog")
        self.changelog_btn.clicked.connect(self._on_changelog)
        maint_row.addWidget(self.update_btn)
        maint_row.addWidget(self.changelog_btn)
        maint_row.addStretch(1)
        try:
            from . import updater
            self.version_label = QtWidgets.QLabel("v" + updater.local_version())
        except Exception:
            self.version_label = QtWidgets.QLabel("")
        self.version_label.setStyleSheet("color: #999;")
        maint_row.addWidget(self.version_label)
        layout.addLayout(maint_row)

        self.report = QtWidgets.QPlainTextEdit()
        self.report.setReadOnly(True)
        self.report.setMinimumHeight(120)
        self.report.setPlaceholderText("Build report appears here.")
        layout.addWidget(self.report, stretch=1)

    # -- browsing -----------------------------------------------------------
    def _browse_fbx(self):
        start = self.fbx_edit.text().strip() or hou.text.expandString("$HIP")
        chosen, _flt = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select mesh FBX", start, "FBX files (*.fbx);;All files (*)")
        if chosen:
            self.fbx_edit.setText(chosen)

    def _browse_anim(self):
        start = self.anim_edit.text().strip() or hou.text.expandString("$HIP")
        chosen, _flt = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select animation FBX", start,
            "FBX files (*.fbx);;All files (*)")
        if chosen:
            self.anim_edit.setText(chosen)
            self._maybe_fill_output()

    def _browse_output(self):
        start = self.out_edit.text().strip() or hou.text.expandString("$HIP")
        chosen, _flt = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save USDC as", start, "USD binary (*.usdc);;All files (*)")
        if chosen:
            self.out_edit.setText(chosen)

    def _maybe_fill_output(self):
        """Auto-fill the output from the animation FBX name (the per-shot
        name), falling back to the mesh FBX. Only if the user hasn't typed an
        output yet."""
        if self.out_edit.text().strip():
            return
        src = self.anim_edit.text().strip() or self.fbx_edit.text().strip()
        if not src:
            return
        stem = os.path.splitext(os.path.basename(src))[0] or "character"
        pattern = self._cfg.get("usdc_output_pattern", "$HIP/usd/{name}.usdc")
        self.out_edit.setText(pattern.format(name=stem))

    def _use_scene_range(self):
        try:
            start, end = hou.playbar.frameRange()
            self.start_spin.setValue(int(start))
            self.end_spin.setValue(int(end))
        except Exception:
            pass
        try:
            self.fps_spin.setValue(int(round(hou.fps())))
        except Exception:
            pass

    # -- build --------------------------------------------------------------
    def _on_build(self):
        fbx = self.fbx_edit.text().strip()
        anim = self.anim_edit.text().strip()
        out = self.out_edit.text().strip()
        if not fbx:
            self._say("Pick the mesh FBX first.")
            return
        if not out:
            self._maybe_fill_output()
            out = self.out_edit.text().strip()
        if not out:
            self._say("Set an output .usdc path.")
            return

        try:
            result = core.build(
                fbx_path=fbx,
                anim_fbx_path=anim,
                usdc_path=out,
                fps=self.fps_spin.value(),
                start=self.start_spin.value(),
                end=self.end_spin.value(),
                write_now=self.write_check.isChecked(),
                cfg=self._cfg,
            )
        except Exception:
            import traceback
            self._say("Build failed:\n%s" % traceback.format_exc())
            return

        self._report_result(result)

    # -- reporting ----------------------------------------------------------
    def _say(self, text):
        self.report.setPlainText(text)

    def _report_result(self, result):
        if "error" in result:
            self._say("ERROR: " + result["error"])
            return

        lines = []
        lines.append("Built network:")
        lines.append("  Geo:          " + result.get("obj_subnet", "?"))
        lines.append("  FBX import:   " + result.get("fbx_node", "?"))
        nulls = result.get("nulls", {})
        lines.append("  Nulls:        %s / %s / %s"
                     % (nulls.get("rest", "?"),
                        nulls.get("capture", "?"),
                        nulls.get("animated", "?")))
        lines.append("  UsdSkel:      " + result.get("usdskel_node", "?"))
        lines.append("  USD ROP:      " + result.get("rop", "?"))
        if result.get("written"):
            lines.append("")
            lines.append("WROTE: " + result.get("usdc", "?"))
        else:
            lines.append("")
            lines.append("Network built (not written). Check it, then press "
                         "the ROP's Save button - or re-run with 'Write USDC "
                         "now' ticked.")
        for w in result.get("warnings", []):
            lines.append("  ! " + w)
        self._say("\n".join(lines))

    # -- updates ------------------------------------------------------------
    def _on_check_updates(self):
        try:
            from . import updater
        except Exception as exc:
            self._say("Updater unavailable: %s" % exc)
            return

        avail, loc, rem = updater.has_update()
        if rem is None:
            self._say("Could not reach GitHub to check for updates "
                      "(network error). Local version: %s" % loc)
            return
        if not avail:
            self._say("Up to date (v%s)." % loc)
            return

        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle("Update available")
        msg.setText("A new version is available.\n\n"
                    "Installed: v%s\nGitHub:    v%s\n\nUpdate now?" % (loc, rem))
        msg.setStandardButtons(QtWidgets.QMessageBox.Yes
                               | QtWidgets.QMessageBox.No)
        if _exec_dialog(msg) != QtWidgets.QMessageBox.Yes:
            self._say("Update skipped. Installed v%s, GitHub v%s." % (loc, rem))
            return

        ok, message = updater.update()
        self._say(message)
        if ok:
            try:
                self.version_label.setText("v" + updater.local_version())
            except Exception:
                pass

    def _on_changelog(self):
        try:
            from . import updater
        except Exception as exc:
            self._say("Updater unavailable: %s" % exc)
            return
        text = updater.remote_changelog()
        if text is None:
            # fall back to the local changelog
            import os
            local = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(
                    os.path.abspath(__file__)))), "CHANGELOG.md")
            try:
                with open(local, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception:
                text = "Changelog unavailable (no network, no local file)."

        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Changelog")
        dlg.setMinimumSize(520, 420)
        lay = QtWidgets.QVBoxLayout(dlg)
        view = QtWidgets.QPlainTextEdit()
        view.setReadOnly(True)
        view.setPlainText(text)
        lay.addWidget(view)
        close = QtWidgets.QPushButton("Close")
        close.clicked.connect(dlg.accept)
        lay.addWidget(close)
        _exec_dialog(dlg)


def show():
    global _dialog
    try:
        parent = hou.qt.mainWindow()
    except Exception:
        parent = None
    _dialog = FbxToUsdcDialog(parent)
    _dialog.show()
    return _dialog
