"""
ui.py - PySide dialog for the FBX -> USDC Converter.

Two tabs:
  - Single: one mesh FBX + one animation FBX -> one .usdc. Pick files, set
    fps/range, choose whether to write immediately and whether to create a
    Reference LOP reading the written file back into the scene.
  - Batch Convert: a table of (mesh, animation, output) rows, converted in one
    pass with shared fps/range/write/reference settings. Covers both batch
    scenarios: many different character+animation pairs (add rows one at a
    time with different mesh/anim each), and one character with many
    animations (pick the mesh once, multi-select animation files, one row per
    file).

Launched from the CGA Tools shelf via:
    from fbx_to_usdc import ui
    ui.show()
"""

import os
import hou

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtWidgets

from . import core
from . import config as _config


def _exec_dialog(d):
    """PySide6 uses exec(); PySide2 uses exec_(). Support both."""
    fn = getattr(d, "exec", None) or getattr(d, "exec_")
    return fn()


def _output_name_for(cfg, mesh_path, anim_path):
    """Same naming rule as core._clean_name: prefer the animation clip name,
    fall back to the mesh name."""
    src = anim_path.strip() if anim_path else ""
    if not src:
        src = mesh_path.strip() if mesh_path else ""
    if not src:
        return ""
    stem = os.path.splitext(os.path.basename(src))[0] or "character"
    pattern = cfg.get("usdc_output_pattern", "$HIP/usd/{name}.usdc")
    return pattern.format(name=stem)


_dialog = None  # keep a reference so the window is not garbage-collected


class FbxToUsdcDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(FbxToUsdcDialog, self).__init__(parent)
        self.setWindowTitle("FBX to USDC Converter")
        self.setMinimumWidth(640)
        self.setMinimumHeight(560)
        self._cfg, cfg_warn = _config.load_config()
        self._build_ui()
        if cfg_warn:
            self._say_single(cfg_warn)

    # -- top-level construction ----------------------------------------------
    def _build_ui(self):
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(8)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self._build_single_tab(), "Single")
        self.tabs.addTab(self._build_batch_tab(), "Batch Convert")
        outer.addWidget(self.tabs, stretch=1)

        # maintenance row: updates + changelog, shared across tabs
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
        outer.addLayout(maint_row)

    # =========================================================================
    # SINGLE TAB
    # =========================================================================
    def _build_single_tab(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(4, 8, 4, 4)
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
        self.scene_btn.clicked.connect(
            lambda: self._use_scene_range(self.fps_spin, self.start_spin, self.end_spin))
        range_row.addWidget(self.scene_btn)
        layout.addLayout(range_row)

        # 5. flags
        self.write_check = QtWidgets.QCheckBox(
            "Write USDC now (unchecked = only build the network)")
        self.write_check.setChecked(bool(self._cfg.get("default_write_now", False)))
        layout.addWidget(self.write_check)

        self.ref_check = QtWidgets.QCheckBox(
            "Create Reference node reading the written file back into /stage")
        self.ref_check.setChecked(bool(self._cfg.get("default_create_reference", False)))
        layout.addWidget(self.ref_check)

        # 6. build + report
        self.build_btn = QtWidgets.QPushButton("Build && Convert")
        self.build_btn.setMinimumHeight(34)
        self.build_btn.clicked.connect(self._on_build)
        layout.addWidget(self.build_btn)

        self.report = QtWidgets.QPlainTextEdit()
        self.report.setReadOnly(True)
        self.report.setMinimumHeight(100)
        self.report.setPlaceholderText("Build report appears here.")
        layout.addWidget(self.report, stretch=1)

        return page

    # -- single: browsing -----------------------------------------------------
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
        text = _output_name_for(self._cfg, self.fbx_edit.text(), self.anim_edit.text())
        if text:
            self.out_edit.setText(text)

    def _use_scene_range(self, fps_spin, start_spin, end_spin):
        try:
            start, end = hou.playbar.frameRange()
            start_spin.setValue(int(start))
            end_spin.setValue(int(end))
        except Exception:
            pass
        try:
            fps_spin.setValue(int(round(hou.fps())))
        except Exception:
            pass

    # -- single: build --------------------------------------------------------
    def _on_build(self):
        fbx = self.fbx_edit.text().strip()
        anim = self.anim_edit.text().strip()
        out = self.out_edit.text().strip()
        if not fbx:
            self._say_single("Pick the mesh FBX first.")
            return
        if not out:
            self._maybe_fill_output()
            out = self.out_edit.text().strip()
        if not out:
            self._say_single("Set an output .usdc path.")
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
                create_reference=self.ref_check.isChecked(),
                cfg=self._cfg,
            )
        except Exception:
            import traceback
            self._say_single("Build failed:\n%s" % traceback.format_exc())
            return

        self._report_single(result)

    # -- single: reporting ------------------------------------------------------
    def _say_single(self, text):
        self.report.setPlainText(text)

    def _report_single(self, result):
        if "error" in result:
            self._say_single("ERROR: " + result["error"])
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
        if result.get("reference_node"):
            lines.append("REFERENCE: " + result["reference_node"])
        for w in result.get("warnings", []):
            lines.append("  ! " + w)
        self._say_single("\n".join(lines))

    # =========================================================================
    # BATCH TAB
    # =========================================================================
    def _build_batch_tab(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)

        hint = QtWidgets.QLabel(
            "Convert many clips in one pass. Covers both cases: several "
            "different character+animation pairs (Add Pair, one at a time), "
            "or one character with many animations (Add Animations for One "
            "Mesh - pick the mesh once, then multi-select the animation "
            "files).")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #999;")
        layout.addWidget(hint)

        # row controls
        add_row = QtWidgets.QHBoxLayout()
        add_pair_btn = QtWidgets.QPushButton("Add Pair...")
        add_pair_btn.clicked.connect(self._batch_add_pair)
        add_many_btn = QtWidgets.QPushButton("Add Animations for One Mesh...")
        add_many_btn.clicked.connect(self._batch_add_many_anims)
        remove_btn = QtWidgets.QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._batch_remove_selected)
        clear_btn = QtWidgets.QPushButton("Clear")
        clear_btn.clicked.connect(self._batch_clear)
        add_row.addWidget(add_pair_btn)
        add_row.addWidget(add_many_btn)
        add_row.addStretch(1)
        add_row.addWidget(remove_btn)
        add_row.addWidget(clear_btn)
        layout.addLayout(add_row)

        # table
        self.batch_table = QtWidgets.QTableWidget(0, 3)
        self.batch_table.setHorizontalHeaderLabels(
            ["Mesh FBX", "Animation FBX", "Output .usdc"])
        header = self.batch_table.horizontalHeader()
        header.setStretchLastSection(True)
        try:
            header.setSectionResizeMode(0, QtWidgets.QHeaderView.Interactive)
            header.setSectionResizeMode(1, QtWidgets.QHeaderView.Interactive)
        except Exception:
            pass
        self.batch_table.setColumnWidth(0, 220)
        self.batch_table.setColumnWidth(1, 220)
        self.batch_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        layout.addWidget(self.batch_table, stretch=1)

        # shared settings
        settings_row = QtWidgets.QHBoxLayout()
        settings_row.addWidget(QtWidgets.QLabel("FPS"))
        self.batch_fps_spin = QtWidgets.QSpinBox()
        self.batch_fps_spin.setRange(1, 240)
        self.batch_fps_spin.setValue(int(self._cfg.get("default_fps", 24)))
        settings_row.addWidget(self.batch_fps_spin)

        settings_row.addSpacing(16)
        settings_row.addWidget(QtWidgets.QLabel("Start"))
        self.batch_start_spin = QtWidgets.QSpinBox()
        self.batch_start_spin.setRange(-100000, 100000)
        self.batch_start_spin.setValue(int(self._cfg.get("default_start", 1)))
        settings_row.addWidget(self.batch_start_spin)

        settings_row.addWidget(QtWidgets.QLabel("End"))
        self.batch_end_spin = QtWidgets.QSpinBox()
        self.batch_end_spin.setRange(-100000, 100000)
        self.batch_end_spin.setValue(int(self._cfg.get("default_end", 240)))
        settings_row.addWidget(self.batch_end_spin)

        settings_row.addStretch(1)
        batch_scene_btn = QtWidgets.QPushButton("Use scene range")
        batch_scene_btn.clicked.connect(
            lambda: self._use_scene_range(self.batch_fps_spin, self.batch_start_spin,
                                          self.batch_end_spin))
        settings_row.addWidget(batch_scene_btn)
        layout.addLayout(settings_row)

        flags_row = QtWidgets.QHBoxLayout()
        self.batch_write_check = QtWidgets.QCheckBox("Write USDC now for each row")
        # Default True for batch (unlike the Single tab): building N networks
        # without writing is rarely what you want when converting a folder.
        self.batch_write_check.setChecked(True)
        flags_row.addWidget(self.batch_write_check)
        self.batch_ref_check = QtWidgets.QCheckBox(
            "Create Reference node per clip")
        self.batch_ref_check.setChecked(bool(self._cfg.get("default_create_reference", False)))
        flags_row.addWidget(self.batch_ref_check)
        flags_row.addStretch(1)
        layout.addLayout(flags_row)

        # convert + report
        self.batch_convert_btn = QtWidgets.QPushButton("Convert All")
        self.batch_convert_btn.setMinimumHeight(34)
        self.batch_convert_btn.clicked.connect(self._on_batch_convert)
        layout.addWidget(self.batch_convert_btn)

        self.batch_report = QtWidgets.QPlainTextEdit()
        self.batch_report.setReadOnly(True)
        self.batch_report.setMinimumHeight(100)
        self.batch_report.setPlaceholderText("Batch report appears here.")
        layout.addWidget(self.batch_report, stretch=1)

        return page

    # -- batch: row management -------------------------------------------------
    def _batch_add_table_row(self, mesh, anim):
        row = self.batch_table.rowCount()
        self.batch_table.insertRow(row)
        self.batch_table.setItem(row, 0, QtWidgets.QTableWidgetItem(mesh))
        self.batch_table.setItem(row, 1, QtWidgets.QTableWidgetItem(anim))
        out = _output_name_for(self._cfg, mesh, anim)
        self.batch_table.setItem(row, 2, QtWidgets.QTableWidgetItem(out))

    def _batch_add_pair(self):
        """Scenario 1: several different character+animation pairs. One call
        adds one row; click again for the next pair with a different mesh."""
        start = hou.text.expandString("$HIP")
        mesh, _flt = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select mesh FBX", start, "FBX files (*.fbx);;All files (*)")
        if not mesh:
            return
        anim, _flt = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select animation FBX", os.path.dirname(mesh),
            "FBX files (*.fbx);;All files (*)")
        # anim may be empty (mesh FBX already carries the animation) - allowed
        self._batch_add_table_row(mesh, anim)

    def _batch_add_many_anims(self):
        """Scenario 2: one character, many animations. Pick the mesh once,
        then multi-select animation files - one row per file, same mesh."""
        start = hou.text.expandString("$HIP")
        mesh, _flt = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select the character mesh FBX (used for all rows below)",
            start, "FBX files (*.fbx);;All files (*)")
        if not mesh:
            return
        anims, _flt = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Select animation FBX files (multi-select)",
            os.path.dirname(mesh), "FBX files (*.fbx);;All files (*)")
        for anim in anims:
            self._batch_add_table_row(mesh, anim)

    def _batch_remove_selected(self):
        rows = sorted(set(idx.row() for idx in self.batch_table.selectedIndexes()),
                     reverse=True)
        for r in rows:
            self.batch_table.removeRow(r)

    def _batch_clear(self):
        self.batch_table.setRowCount(0)
        self.batch_report.setPlainText("")

    # -- batch: convert ---------------------------------------------------------
    def _on_batch_convert(self):
        n = self.batch_table.rowCount()
        if n == 0:
            self.batch_report.setPlainText(
                "No rows to convert. Use 'Add Pair...' or 'Add Animations for "
                "One Mesh...' first.")
            return

        fps = self.batch_fps_spin.value()
        start = self.batch_start_spin.value()
        end = self.batch_end_spin.value()
        write_now = self.batch_write_check.isChecked()
        create_reference = self.batch_ref_check.isChecked()

        lines = []
        ok_count = 0
        for row in range(n):
            mesh = self._batch_cell(row, 0)
            anim = self._batch_cell(row, 1)
            out = self._batch_cell(row, 2)
            label = os.path.basename(anim) if anim else os.path.basename(mesh)

            if not mesh:
                lines.append("[skip] row %d: no mesh FBX set" % (row + 1))
                continue
            if not out:
                out = _output_name_for(self._cfg, mesh, anim)

            try:
                result = core.build(
                    fbx_path=mesh,
                    anim_fbx_path=anim,
                    usdc_path=out,
                    fps=fps,
                    start=start,
                    end=end,
                    write_now=write_now,
                    create_reference=create_reference,
                    cfg=self._cfg,
                )
            except Exception:
                import traceback
                lines.append("[FAIL] %s: %s" % (label, traceback.format_exc().splitlines()[-1]))
                continue

            if "error" in result:
                lines.append("[FAIL] %s: %s" % (label, result["error"]))
                continue

            ok_count += 1
            tag = "WROTE" if result.get("written") else "BUILT"
            line = "[%s] %s -> %s" % (tag, label, result.get("usdc", out))
            if result.get("reference_node"):
                line += "  (ref: %s)" % result["reference_node"]
            lines.append(line)
            for w in result.get("warnings", []):
                lines.append("      ! " + w)

        lines.append("")
        lines.append("Done: %d / %d succeeded." % (ok_count, n))
        self.batch_report.setPlainText("\n".join(lines))

    def _batch_cell(self, row, col):
        item = self.batch_table.item(row, col)
        return item.text().strip() if item is not None else ""

    # =========================================================================
    # SHARED: updates / changelog
    # =========================================================================
    def _on_check_updates(self):
        try:
            from . import updater
        except Exception as exc:
            self._say_single("Updater unavailable: %s" % exc)
            return

        avail, loc, rem = updater.has_update()
        if rem is None:
            self._say_single("Could not reach GitHub to check for updates "
                             "(network error). Local version: %s" % loc)
            return
        if not avail:
            self._say_single("Up to date (v%s)." % loc)
            return

        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle("Update available")
        msg.setText("A new version is available.\n\n"
                    "Installed: v%s\nGitHub:    v%s\n\nUpdate now?" % (loc, rem))
        msg.setStandardButtons(QtWidgets.QMessageBox.Yes
                               | QtWidgets.QMessageBox.No)
        if _exec_dialog(msg) != QtWidgets.QMessageBox.Yes:
            self._say_single("Update skipped. Installed v%s, GitHub v%s." % (loc, rem))
            return

        ok, message = updater.update()
        self._say_single(message)
        if ok:
            try:
                self.version_label.setText("v" + updater.local_version())
            except Exception:
                pass

    def _on_changelog(self):
        try:
            from . import updater
        except Exception as exc:
            self._say_single("Updater unavailable: %s" % exc)
            return
        text = updater.remote_changelog()
        if text is None:
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
