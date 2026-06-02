# __init__.py
# Copyright (C) 2026 Chai Chaimee
# Licensed under GNU General Public License. See COPYING.txt for details.

import os
import api
import ui
import scriptHandler
import globalPluginHandler
import addonHandler
import tones
import logHandler
import core
import time
import wx
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

	def getScript(self, gesture):
		if not self.inLayeredMode:
			return super().getScript(gesture)

		# Use gesture identifiers (language-independent) instead of displayName
		for identifier in gesture.identifiers:
			identifier_lower = identifier.lower()
			
			if identifier_lower in ("kb:escape", "kb:q"):
				return self.script_hideLayerMode
			elif identifier_lower in ("kb:space", "kb:c"):
				return self.script_togglePause
			elif identifier_lower == "kb:rightarrow":
				return self.script_seekForward
			elif identifier_lower == "kb:leftarrow":
				return self.script_seekBackward
			elif identifier_lower == "kb:pageup":
				return self.script_volUp
			elif identifier_lower == "kb:pagedown":
				return self.script_volDown
			elif identifier_lower == "kb:uparrow":
				return self.script_prevFile
			elif identifier_lower == "kb:downarrow":
				return self.script_nextFile
			elif identifier_lower == "kb:x":
				return self.script_restartFile
			elif identifier_lower == "kb:z":
				return self.script_clearData
			elif identifier_lower == "kb:w":
				return self.script_currentTime
			elif identifier_lower == "kb:e":
				return self.script_seekToLast10
			elif identifier_lower == "kb:r":
				return self.script_remainingTime
			elif identifier_lower == "kb:t":
				return self.script_totalTime
			elif identifier_lower == "kb:b":
				return self.script_setBookmark
			elif identifier_lower == "kb:ctrl+b":
				return self.script_nextBookmark
			elif identifier_lower == "kb:shift+b":
				return self.script_prevBookmark

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
		except:
			return None, None, None

	def _get_audio_files_in_folder(self, folder):
		files = []
		try:
			for f in os.listdir(folder):
				if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS:
					files.append(f)
			return sorted(files)
		except:
			return []

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

	def event_gainFocus(self, obj, nextHandler):
		if not self.current_file_path or not self.target_window_handle:
			nextHandler()
			return

		try:
			fg_handle = api.getForegroundObject().windowHandle
			is_target_window = (fg_handle == self.target_window_handle)
			
			if is_target_window and not self.inLayeredMode:
				self.inLayeredMode = True
				if self.player and self.current_file_path:
					if not self.player.is_playing():
						self.player.play()
				tones.beep(800, 40)
				ui.message(_("Listen Mode Active"))
			elif not is_target_window and self.inLayeredMode:
				self.inLayeredMode = False
				tones.beep(200, 40)
				ui.message(_("Listen Mode Hidden"))
		except Exception as e:
			logHandler.log.debug(f"event_gainFocus error: {e}")
		nextHandler()

	def _execute_tap_action(self):
		if self.tap_count == 1:
			if not self.current_file_path:
				path, window_handle, folder_path = self._get_path_from_explorer()
				if path:
					self._perform_enter_layer(path, window_handle, folder_path)
				else:
					ui.message(_("Select Audio File"))
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
			if self.player and self.current_file_path:
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
			except:
				pass
		
		self._pending_tap_action = wx.CallLater(int(TAP_THRESHOLD * 1000), self._execute_tap_action)

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
		if self.player and self.current_file_path:
			self.player.toggle_pause()

	@scriptHandler.script(
		description="Seek forward 10 seconds",
		category="Listen",
		gesture=None
	)
	def script_seekForward(self, gesture):
		if self.player and self.current_file_path:
			self.player.seek(10)

	@scriptHandler.script(
		description="Seek backward 10 seconds",
		category="Listen",
		gesture=None
	)
	def script_seekBackward(self, gesture):
		if self.player and self.current_file_path:
			self.player.seek(-10)

	@scriptHandler.script(
		description="Increase volume",
		category="Listen",
		gesture=None
	)
	def script_volUp(self, gesture):
		if self.player and self.current_file_path:
			self.player.change_volume(2)

	@scriptHandler.script(
		description="Decrease volume",
		category="Listen",
		gesture=None
	)
	def script_volDown(self, gesture):
		if self.player and self.current_file_path:
			self.player.change_volume(-2)

	@scriptHandler.script(
		description="Restart current file",
		category="Listen",
		gesture=None
	)
	def script_restartFile(self, gesture):
		if self.player and self.current_file_path:
			self.player.restart_current()

	@scriptHandler.script(
		description="Clear playback history",
		category="Listen",
		gesture=None
	)
	def script_clearData(self, gesture):
		if self.player and self.current_file_path:
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
			if self.player:
				was_playing = self.player.is_playing()
				self.player.stop(self.current_file_path)
			current_name = os.path.basename(self.current_file_path)
			if current_name in files:
				idx = files.index(current_name)
			else:
				idx = 0
			new_idx = (idx + delta) % len(files)
			new_path = os.path.join(folder, files[new_idx])
			if self.player and self.player.load(new_path):
				self.current_file_path = new_path
				if was_playing or self.inLayeredMode:
					self.player.play()
				ui.message(files[new_idx])
		except Exception as e:
			logHandler.log.debug(f"Navigate error: {e}")

	@scriptHandler.script(
		description="Show current playback position",
		category="Listen",
		gesture=None
	)
	def script_currentTime(self, gesture):
		if self.player and self.current_file_path:
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
		if self.player and self.current_file_path:
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
		if self.player and self.current_file_path:
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
		if self.player and self.current_file_path:
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
		if self.player and self.current_file_path:
			current_pos = self.player.get_position()
			self.player.add_bookmark(current_pos)

	@scriptHandler.script(
		description="Go to next bookmark",
		category="Listen",
		gesture=None
	)
	def script_nextBookmark(self, gesture):
		if self.player and self.current_file_path:
			if not self.player.go_to_next_bookmark():
				tones.beep(100, 100)

	@scriptHandler.script(
		description="Go to previous bookmark",
		category="Listen",
		gesture=None
	)
	def script_prevBookmark(self, gesture):
		if self.player and self.current_file_path:
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
			except:
				pass
		if self.player:
			self.player.stop(self.current_file_path)
		super().terminate()