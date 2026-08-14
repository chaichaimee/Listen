# __init__.py
# Copyright (C) 2026 Chai Chaimee
# Licensed under GNU General Public License. See COPYING.txt for details.

import os
import threading
import api
import ui
import scriptHandler
import globalPluginHandler
import addonHandler
import tones
import logHandler
import core
import time
import winUser
import wx
import comtypes
from . import audio_engine

addonHandler.initTranslation()

SUPPORTED_EXTENSIONS = ('.mp3', '.wav', '.wma', '.m4a', '.flac', '.aac', '.ogg', '.opus', '.mid', '.midi')
TAP_THRESHOLD = 0.5

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self):
		super(GlobalPlugin, self).__init__()
		self.player = audio_engine.AudioPlayer()
		self.inLayeredMode = False
		self.current_file_path = None
		self.target_window_handle = None
		self.target_folder_path = None
		self.last_tap_time = 0
		self.tap_count = 0
		self._pending_tap_action = None
		self._isResolvingExplorerTarget = False

	# Layer key map is keyed on (mainKeyName, modifierNames) instead of the
	# raw "kb:x" identifier string. Identifier strings are composed
	# differently depending on the active NVDA keyboard settings layout and
	# on whether the gesture carries a laptop/desktop qualifier, which was
	# silently dropping every match in this method and letting the raw
	# keystroke fall through to the focused Explorer window.
	_LAYER_KEY_MAP = {
		("escape", frozenset()): "script_hideLayerMode",
		("q", frozenset()): "script_hideLayerMode",
		("space", frozenset()): "script_togglePause",
		("c", frozenset()): "script_togglePause",
		("rightarrow", frozenset()): "script_seekForward",
		("leftarrow", frozenset()): "script_seekBackward",
		("pageup", frozenset()): "script_volUp",
		("pagedown", frozenset()): "script_volDown",
		("uparrow", frozenset()): "script_prevFile",
		("downarrow", frozenset()): "script_nextFile",
		("x", frozenset()): "script_restartFile",
		("z", frozenset()): "script_clearData",
		("w", frozenset()): "script_currentTime",
		("e", frozenset()): "script_seekToLast10",
		("r", frozenset()): "script_remainingTime",
		("t", frozenset()): "script_totalTime",
		("b", frozenset()): "script_setBookmark",
		("b", frozenset({"control"})): "script_nextBookmark",
		("b", frozenset({"shift"})): "script_prevBookmark",
	}

	# Bare modifier presses (e.g. holding Alt or Windows while tapping the
	# other half of a combo) can never match _LAYER_KEY_MAP on their own and
	# fire repeatedly under key auto-repeat, so they are filtered out before
	# doing any dict work or logging.
	_MODIFIER_ONLY_KEY_NAMES = frozenset({
		"leftcontrol", "rightcontrol",
		"leftshift", "rightshift",
		"leftalt", "rightalt",
		"leftwindows", "rightwindows",
	})

	def getScript(self, gesture):
		if not self.inLayeredMode:
			return super().getScript(gesture)

		try:
			mainKeyName = getattr(gesture, "mainKeyName", None)
			if not mainKeyName or mainKeyName.lower() in self._MODIFIER_ONLY_KEY_NAMES:
				return super().getScript(gesture)
			modifierNames = frozenset(name.lower() for name in getattr(gesture, "modifierNames", ()))
			scriptAttrName = self._LAYER_KEY_MAP.get((mainKeyName.lower(), modifierNames))
			if scriptAttrName:
				return getattr(self, scriptAttrName)
		except AttributeError as e:
			logHandler.log.error(f"Listen: getScript layer dispatch failed: {e}", exc_info=True)

		return super().getScript(gesture)

	def _get_path_from_explorer(self):
		try:
			from comtypes.client import CreateObject as COMCreate
			fg = api.getForegroundObject()
			shell = COMCreate("Shell.Application")
			for window in shell.Windows():
				if window.hwnd == fg.windowHandle:
					item = window.Document.FocusedItem
					if item and item.Path:
						ext = os.path.splitext(item.Path)[1].lower()
						if ext in SUPPORTED_EXTENSIONS:
							return item.Path, fg.windowHandle, os.path.dirname(item.Path)
			return None, None, None
		except Exception as e:
			logHandler.log.debug(f"Listen: _get_path_from_explorer error: {e}")
			return None, None, None

	def _get_audio_files_in_folder(self, folder):
		files = []
		try:
			for f in os.listdir(folder):
				if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS:
					files.append(f)
			return sorted(files)
		except Exception as e:
			logHandler.log.debug(f"Listen: _get_audio_files_in_folder error: {e}")
			return []

	def _resolve_explorer_target_async(self):
		if self._isResolvingExplorerTarget:
			return
		self._isResolvingExplorerTarget = True
		workerThread = threading.Thread(target=self._explorer_lookup_worker, daemon=True)
		workerThread.start()

	def _explorer_lookup_worker(self):
		comtypes.CoInitialize()
		try:
			path, windowHandle, folderPath = self._get_path_from_explorer()
		except Exception as e:
			logHandler.log.debug(f"Listen: _explorer_lookup_worker error: {e}")
			path, windowHandle, folderPath = None, None, None
		finally:
			comtypes.CoUninitialize()
		wx.CallAfter(self._handle_explorer_lookup_result, path, windowHandle, folderPath)

	def _handle_explorer_lookup_result(self, path, window_handle, folder_path):
		self._isResolvingExplorerTarget = False
		if path:
			self._perform_enter_layer(path, window_handle, folder_path)
		else:
			ui.message(_("Select Audio File"))

	def _perform_enter_layer(self, path, window_handle, folder_path):
		logHandler.log.debug(f"Listen: Attempting to load {path}")
		if self.player.load(path):
			self.inLayeredMode = True
			self.current_file_path = path
			self.target_window_handle = window_handle
			self.target_folder_path = folder_path
			self.player.play()
			tones.beep(800, 40)
			ui.message(_("Listen Mode Active"))
		else:
			logHandler.log.warning(f"Listen: Failed to load {path}")
			ui.message(_("Error loading file"))

	def _update_layer_state(self, active_hwnd):
		if not self.current_file_path or not self.target_window_handle:
			return

		is_target_window = (active_hwnd == self.target_window_handle)

		if is_target_window and not self.inLayeredMode:
			self.inLayeredMode = True
			if getattr(self, "player", None) and self.current_file_path:
				if not self.player.is_playing():
					self.player.play()
			tones.beep(800, 40)
			ui.message(_("Listen Mode Active"))
		elif not is_target_window and self.inLayeredMode:
			self.inLayeredMode = False
			tones.beep(200, 40)
			ui.message(_("Listen Mode Hidden"))

	def event_foreground(self, obj, nextHandler):
		try:
			if self.current_file_path and self.target_window_handle:
				fg_handle = getattr(obj, "windowHandle", 0)
				self._update_layer_state(fg_handle)
		except Exception as e:
			logHandler.log.debug(f"Listen: event_foreground error: {e}")
			
		nextHandler()

	def event_gainFocus(self, obj, nextHandler):
		# WATCHDOG: O(1) Fast check to bypass UIA calls instantly if Listen Mode is inactive
		if not self.current_file_path or not self.target_window_handle:
			return nextHandler()

		try:
			# Use the real system foreground window, not GA_ROOT of the focused
			# object. Transient popups (context menu, type-ahead search box, rename
			# edit) are often separate top-level windows whose GA_ROOT does not
			# resolve back to Explorer, which was causing a false "window changed"
			# detection and silently dropping Listen Mode to Hidden.
			fg_hwnd = winUser.getForegroundWindow()
			if fg_hwnd:
				self._update_layer_state(fg_hwnd)
		except Exception as e:
			logHandler.log.debug(f"Listen: event_gainFocus error: {e}")
			
		nextHandler()

	def _execute_tap_action(self):
		if self.tap_count == 1:
			if not self.current_file_path:
				self._resolve_explorer_target_async()
			else:
				if not self.inLayeredMode:
					self.inLayeredMode = True
					if self.player and self.current_file_path:
						if not self.player.is_playing():
							self.player.play()
					tones.beep(800, 40)
					ui.message(_("Listen Mode Active"))
				else:
					tones.beep(600, 40)
		
		elif self.tap_count == 2:
			if getattr(self, "player", None) and self.current_file_path:
				self.player.stop(self.current_file_path)
			self.inLayeredMode = False
			self.current_file_path = None
			self.target_window_handle = None
			self.target_folder_path = None
			tones.beep(150, 40)
			ui.message(_("Permanently Stopped"))
		
		self.tap_count = 0
		self._pending_tap_action = None

	@scriptHandler.script(
		description="Listen Mode (Single: Show/Hide, Double: Permanent Stop)",
		category="Listen",
		gesture="kb:alt+windows+l"
	)
	def script_handleListenMode(self, gesture):
		current_time = time.time()
		
		if current_time - self.last_tap_time > TAP_THRESHOLD:
			self.tap_count = 0
		
		self.tap_count += 1
		self.last_tap_time = current_time
		
		if self._pending_tap_action:
			try:
				self._pending_tap_action.Stop()
			except Exception:
				pass
		
		self._pending_tap_action = core.callLater(int(TAP_THRESHOLD * 1000), self._execute_tap_action)

	@scriptHandler.script(
		description="Hide Listen Mode (Audio continues)",
		category="Listen",
		gesture="kb:q"
	)
	def script_hideLayerMode(self, gesture):
		if not self.current_file_path:
			gesture.send()
			return
		
		if self.inLayeredMode:
			self.inLayeredMode = False
			tones.beep(200, 40)
			ui.message(_("Listen Mode Hidden"))
		else:
			gesture.send()

	@scriptHandler.script(
		description="Toggle play/pause",
		category="Listen",
		gesture=None
	)
	def script_togglePause(self, gesture):
		if getattr(self, "player", None) and self.current_file_path:
			self.player.toggle_pause()

	@scriptHandler.script(
		description="Seek forward 10 seconds",
		category="Listen",
		gesture=None
	)
	def script_seekForward(self, gesture):
		if getattr(self, "player", None) and self.current_file_path:
			self.player.seek(10)

	@scriptHandler.script(
		description="Seek backward 10 seconds",
		category="Listen",
		gesture=None
	)
	def script_seekBackward(self, gesture):
		if getattr(self, "player", None) and self.current_file_path:
			self.player.seek(-10)

	@scriptHandler.script(
		description="Increase volume",
		category="Listen",
		gesture=None
	)
	def script_volUp(self, gesture):
		if getattr(self, "player", None) and self.current_file_path:
			self.player.change_volume(2)

	@scriptHandler.script(
		description="Decrease volume",
		category="Listen",
		gesture=None
	)
	def script_volDown(self, gesture):
		if getattr(self, "player", None) and self.current_file_path:
			self.player.change_volume(-2)

	@scriptHandler.script(
		description="Restart current file",
		category="Listen",
		gesture=None
	)
	def script_restartFile(self, gesture):
		if getattr(self, "player", None) and self.current_file_path:
			self.player.restart_current()

	@scriptHandler.script(
		description="Clear playback history",
		category="Listen",
		gesture=None
	)
	def script_clearData(self, gesture):
		if getattr(self, "player", None) and self.current_file_path:
			self.player.clear_positions()
			tones.beep(400, 50)
			ui.message(_("History Cleared"))

	@scriptHandler.script(
		description="Previous audio file",
		category="Listen",
		gesture=None
	)
	def script_prevFile(self, gesture):
		self._navigate(-1)

	@scriptHandler.script(
		description="Next audio file",
		category="Listen",
		gesture=None
	)
	def script_nextFile(self, gesture):
		self._navigate(1)

	def _navigate(self, delta):
		if not self.current_file_path:
			return
		folder = os.path.dirname(self.current_file_path)
		files = self._get_audio_files_in_folder(folder)
		if not files:
			ui.message(_("No audio files in folder"))
			return
		try:
			was_playing = False
			if getattr(self, "player", None):
				was_playing = self.player.is_playing()
				self.player.stop(self.current_file_path)
			current_name = os.path.basename(self.current_file_path)
			if current_name in files:
				idx = files.index(current_name)
			else:
				idx = 0
			new_idx = (idx + delta) % len(files)
			new_path = os.path.join(folder, files[new_idx])
			if getattr(self, "player", None) and self.player.load(new_path):
				self.current_file_path = new_path
				if was_playing or self.inLayeredMode:
					self.player.play()
				ui.message(files[new_idx])
		except Exception as e:
			logHandler.log.debug(f"Listen: Navigate error: {e}")

	@scriptHandler.script(
		description="Show current playback position",
		category="Listen",
		gesture=None
	)
	def script_currentTime(self, gesture):
		if getattr(self, "player", None) and self.current_file_path:
			pos = self.player.get_position()
			if pos is not None:
				ui.message(self._format_time(pos))
			else:
				tones.beep(200, 50)

	@scriptHandler.script(
		description="Show remaining time",
		category="Listen",
		gesture=None
	)
	def script_remainingTime(self, gesture):
		if getattr(self, "player", None) and self.current_file_path:
			pos = self.player.get_position()
			total = self.player.get_total_length()
			if pos is not None and total is not None:
				remaining = max(0, total - pos)
				ui.message(self._format_time(remaining))
			else:
				tones.beep(200, 50)

	@scriptHandler.script(
		description="Show total duration",
		category="Listen",
		gesture=None
	)
	def script_totalTime(self, gesture):
		if getattr(self, "player", None) and self.current_file_path:
			total = self.player.get_total_length()
			if total is not None:
				ui.message(self._format_time(total))
			else:
				tones.beep(200, 50)

	@scriptHandler.script(
		description="Seek to last 10 seconds",
		category="Listen",
		gesture=None
	)
	def script_seekToLast10(self, gesture):
		if getattr(self, "player", None) and self.current_file_path:
			total = self.player.get_total_length()
			if total is not None:
				seek_to = max(0, total - 10000)
				self.player.seek_to(seek_to)
			else:
				tones.beep(200, 50)

	@scriptHandler.script(
		description="Add bookmark at current position",
		category="Listen",
		gesture=None
	)
	def script_setBookmark(self, gesture):
		if getattr(self, "player", None) and self.current_file_path:
			current_pos = self.player.get_position()
			self.player.add_bookmark(current_pos)

	@scriptHandler.script(
		description="Go to next bookmark",
		category="Listen",
		gesture=None
	)
	def script_nextBookmark(self, gesture):
		if getattr(self, "player", None) and self.current_file_path:
			if not self.player.go_to_next_bookmark():
				tones.beep(100, 100)

	@scriptHandler.script(
		description="Go to previous bookmark",
		category="Listen",
		gesture=None
	)
	def script_prevBookmark(self, gesture):
		if getattr(self, "player", None) and self.current_file_path:
			if not self.player.go_to_prev_bookmark():
				tones.beep(100, 100)

	def _format_time(self, ms):
		seconds = ms // 1000
		hours = seconds // 3600
		minutes = (seconds % 3600) // 60
		seconds = seconds % 60
		if hours > 0:
			return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
		else:
			return f"{minutes:02d}:{seconds:02d}"

	def terminate(self):
		if self._pending_tap_action:
			try:
				self._pending_tap_action.Stop()
			except Exception:
				pass
		if getattr(self, "player", None):
			self.player.stop(self.current_file_path)
		super().terminate()
