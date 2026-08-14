# Copyright (C) 2026 Chai Chaimee
# Licensed under GNU General Public License. See COPYING.txt for details.

import os
import json
import globalVars
import logHandler
import tones
import core
from ctypes import windll, create_unicode_buffer, byref, c_uint

BOOKMARK_CHIME_GAP_MS = 90

class AudioPlayer:
	def __init__(self):
		self.config_dir = os.path.join(globalVars.appArgs.configPath, "ChaiChaimee")
		self.config_path = os.path.join(self.config_dir, "listen.json")
		self.data = self._load_config()
		self.alias = "ChaiListenPlayer"
		self._volume = self.data.get("volume", 40)
		self._is_wav = False
		self._original_wave_volume = None
		self._bookmarks = []
		self._current_bookmark_index = -1
		self._current_file_path = None
		self._is_loaded = False

	def _load_config(self):
		if not os.path.exists(self.config_dir):
			os.makedirs(self.config_dir)
		if not os.path.exists(self.config_path):
			default = {"volume": 40, "positions": {}, "bookmarks": {}}
			try:
				with open(self.config_path, 'w', encoding='utf-8') as f:
					json.dump(default, f, indent=4)
			except Exception as e:
				logHandler.log.debug(f"Listen: Failed to create default config: {e}")
			return default
		try:
			with open(self.config_path, 'r', encoding='utf-8') as f:
				return json.load(f)
		except Exception as e:
			logHandler.log.debug(f"Listen: Failed to load config: {e}")
			return {"volume": 40, "positions": {}, "bookmarks": {}}

	def _send_command(self, cmd):
		buffer = create_unicode_buffer(255)
		windll.winmm.mciSendStringW(cmd, buffer, 254, 0)
		result = buffer.value
		if result and "error" in result.lower():
			logHandler.log.debug(f"MCI command '{cmd}' returned: {result}")
		return result

	def _get_wave_volume(self):
		try:
			vol = c_uint()
			result = windll.winmm.waveOutGetVolume(0, byref(vol))
			if result == 0:
				left = vol.value & 0xFFFF
				right = (vol.value >> 16) & 0xFFFF
				avg = (left + right) // 2
				return int(avg * 100 / 0xFFFF)
			else:
				logHandler.log.debug(f"waveOutGetVolume failed with error {result}")
				return None
		except Exception as e:
			logHandler.log.debug(f"waveOutGetVolume exception: {e}")
			return None

	def _set_wave_volume(self, percent):
		try:
			if percent < 0:
				percent = 0
			if percent > 100:
				percent = 100
			val = int(percent * 0xFFFF / 100)
			vol = (val << 16) | val
			result = windll.winmm.waveOutSetVolume(0, vol)
			if result != 0:
				logHandler.log.debug(f"waveOutSetVolume failed with error {result}")
		except Exception as e:
			logHandler.log.debug(f"waveOutSetVolume exception: {e}")

	def load(self, path):
		self._send_command(f"close {self.alias}")
		ext = os.path.splitext(path)[1].lower()
		self._is_wav = (ext == '.wav')
		self._current_file_path = path

		if ext == '.wav':
			res = self._send_command(f'open "{path}" alias {self.alias}')
			if "error" in res.lower():
				logHandler.log.warning(f"Listen: Failed to open WAV {path}: {res}")
				return False
			self._original_wave_volume = self._get_wave_volume()
			self._set_wave_volume(self._volume)
		elif ext == '.mp3':
			res = self._send_command(f'open "{path}" type MPEGVideo alias {self.alias}')
			if "error" in res.lower():
				res = self._send_command(f'open "{path}" alias {self.alias}')
			if "error" in res.lower():
				logHandler.log.warning(f"Listen: Failed to open MP3 {path}: {res}")
				return False
			self.set_volume(self._volume)
		else:
			res = self._send_command(f'open "{path}" alias {self.alias}')
			if "error" in res.lower():
				logHandler.log.warning(f"Listen: Failed to open {path}: {res}")
				return False
			self.set_volume(self._volume)

		self._bookmarks = self.data.get("bookmarks", {}).get(path, [])
		self._current_bookmark_index = -1 if not self._bookmarks else 0

		last_pos = self.data.get("positions", {}).get(path, 0)
		if last_pos > 0:
			self._send_command(f"seek {self.alias} to {last_pos}")
		self._is_loaded = True
		return True

	def play(self):
		if not self._is_loaded:
			return
		if self._is_wav:
			self._set_wave_volume(self._volume)
		else:
			self.set_volume(self._volume)
		self._send_command(f"play {self.alias}")

	def stop(self, current_file=None):
		if not self._is_loaded:
			return
		if current_file and self._current_file_path == current_file:
			pos = self._send_command(f"status {self.alias} position")
			try:
				if pos and pos.isdigit():
					self.data["positions"][current_file] = int(pos)
					self.data["bookmarks"][current_file] = self._bookmarks
			except Exception:
				pass
		self.data["volume"] = self._volume
		self._send_command(f"stop {self.alias}")
		self._send_command(f"close {self.alias}")
		if self._is_wav and self._original_wave_volume is not None:
			self._set_wave_volume(self._original_wave_volume)
			self._original_wave_volume = None
		self.save_data()
		self._is_wav = False
		self._bookmarks = []
		self._current_bookmark_index = -1
		self._current_file_path = None
		self._is_loaded = False

	def is_playing(self):
		if not self._is_loaded or not self._current_file_path:
			return False
		status = self._send_command(f"status {self.alias} mode")
		return "playing" in status.lower()

	def save_data(self):
		try:
			with open(self.config_path, 'w', encoding='utf-8') as f:
				json.dump(self.data, f, indent=4)
		except Exception as e:
			logHandler.log.debug(f"Listen: Failed to save config: {e}")

	def clear_positions(self):
		self.data["positions"] = {}
		self.data["bookmarks"] = {}
		self.save_data()
		self._bookmarks = []
		self._current_bookmark_index = -1

	def restart_current(self):
		if not self._is_loaded:
			return
		self._send_command(f"seek {self.alias} to 0")
		if self._is_wav:
			self._set_wave_volume(self._volume)
		else:
			self.set_volume(self._volume)
		self._send_command(f"play {self.alias}")

	def toggle_pause(self):
		if not self._is_loaded:
			return
		status = self._send_command(f"status {self.alias} mode")
		if "playing" in status.lower():
			self._send_command(f"pause {self.alias}")
		else:
			if self._is_wav:
				self._set_wave_volume(self._volume)
			else:
				self.set_volume(self._volume)
			self._send_command(f"play {self.alias}")

	def seek(self, seconds):
		if not self._is_loaded:
			return
		curr = self._send_command(f"status {self.alias} position")
		try:
			new_pos = int(curr) + (seconds * 1000)
			self._send_command(f"seek {self.alias} to {max(0, new_pos)}")
			if self._is_wav:
				self._set_wave_volume(self._volume)
			else:
				self.set_volume(self._volume)
			self._send_command(f"play {self.alias}")
		except Exception:
			pass

	def seek_to(self, ms):
		if not self._is_loaded:
			return
		try:
			self._send_command(f"seek {self.alias} to {max(0, ms)}")
			if self._is_wav:
				self._set_wave_volume(self._volume)
			else:
				self.set_volume(self._volume)
			self._send_command(f"play {self.alias}")
		except Exception:
			pass

	def set_volume(self, value):
		self._volume = max(0, min(100, value))
		mci_vol = self._volume * 10
		self._send_command(f"setaudio {self.alias} volume to {mci_vol}")

	def change_volume(self, delta):
		self.set_volume(self._volume + delta)
		if self._is_wav:
			self._set_wave_volume(self._volume)

	def get_position(self):
		if not self._is_loaded:
			return None
		pos = self._send_command(f"status {self.alias} position")
		try:
			return int(pos) if pos else None
		except Exception:
			return None

	def get_total_length(self):
		if not self._is_loaded:
			return None
		length = self._send_command(f"status {self.alias} length")
		try:
			return int(length) if length else None
		except Exception:
			return None

	def add_bookmark(self, position_ms):
		if position_ms is None or not self._is_loaded:
			tones.beep(200, 50)
			return
		
		for existing in self._bookmarks:
			if abs(existing - position_ms) < 500:
				tones.beep(300, 50)
				return
		
		self._bookmarks.append(position_ms)
		self._bookmarks.sort()
		self._current_bookmark_index = self._bookmarks.index(position_ms)
		bookmarkCount = len(self._bookmarks)
		tones.beep(1200, 30)
		if bookmarkCount > 1:
			# Deferred and pitched differently from the first chime so it is
			# actually audible; two identical 1200Hz beeps fired back to
			# back with no gap render as a single tone (or get clipped by
			# the audio backend), which is why bookmark 2+ sounded silent.
			core.callLater(BOOKMARK_CHIME_GAP_MS, tones.beep, 1500, 30)

	def go_to_next_bookmark(self):
		if not self._bookmarks or not self._is_loaded:
			return False
		if self._current_bookmark_index + 1 < len(self._bookmarks):
			self._current_bookmark_index += 1
			target_pos = self._bookmarks[self._current_bookmark_index]
			self.seek_to(target_pos)
			tones.beep(800, 40)
			return True
		return False

	def go_to_prev_bookmark(self):
		if not self._bookmarks or not self._is_loaded:
			return False
		if self._current_bookmark_index - 1 >= 0:
			self._current_bookmark_index -= 1
			target_pos = self._bookmarks[self._current_bookmark_index]
			self.seek_to(target_pos)
			tones.beep(800, 40)
			return True
		return False
