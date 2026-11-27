# listenConfig.py

import os
import json
import shutil
import addonHandler
import globalVars
import logHandler

VENDOR_DIR_NAME = "ChaiChaimee"
ADDON_DIR_NAME = "Listen"
CONFIG_FILE_NAME = "listen.json"
VERSION_KEY = "addonVersion"


def getDefaultData():
	return {"volume": 40, "positions": {}, "bookmarks": {}}


def getConfigDir():
	return os.path.join(globalVars.appArgs.configPath, VENDOR_DIR_NAME, ADDON_DIR_NAME)


def getConfigPath():
	return os.path.join(getConfigDir(), CONFIG_FILE_NAME)


def getLegacyConfigPath():
	return os.path.join(globalVars.appArgs.configPath, VENDOR_DIR_NAME, CONFIG_FILE_NAME)


def getInstalledVersion():
	try:
		codeAddon = addonHandler.getCodeAddon()
		return str(codeAddon.version) if codeAddon else ""
	except (AssertionError, AttributeError, TypeError, KeyError) as e:
		logHandler.log.debug(f"Listen: could not read installed version: {e}")
		return ""


def writeJsonAtomic(targetPath, payload):
	tempPath = targetPath + ".tmp"
	backupPath = targetPath + ".bak"
	with open(tempPath, "w", encoding="utf-8") as tempFile:
		json.dump(payload, tempFile, indent=4)
		tempFile.flush()
		os.fsync(tempFile.fileno())
	if os.path.isfile(targetPath):
		try:
			shutil.copyfile(targetPath, backupPath)
		except OSError as e:
			logHandler.log.debug(f"Listen: backup of {targetPath} skipped: {e}")
	os.replace(tempPath, targetPath)


def _readJsonDict(path):
	try:
		with open(path, "r", encoding="utf-8") as jsonFile:
			loaded = json.load(jsonFile)
	except (OSError, ValueError) as e:
		logHandler.log.debug(f"Listen: could not read {path}: {e}")
		return None
	return loaded if isinstance(loaded, dict) else None


def migrateLegacyConfig():
	legacyPath = getLegacyConfigPath()
	if not os.path.isfile(legacyPath):
		return False
	newPath = getConfigPath()
	try:
		os.makedirs(getConfigDir(), exist_ok=True)
		if _readJsonDict(newPath) is None:
			with open(legacyPath, "rb") as legacyFile:
				rawBytes = legacyFile.read()
			tempPath = newPath + ".tmp"
			with open(tempPath, "wb") as tempFile:
				tempFile.write(rawBytes)
				tempFile.flush()
				os.fsync(tempFile.fileno())
			os.replace(tempPath, newPath)
			with open(newPath, "rb") as verifyFile:
				if verifyFile.read() != rawBytes:
					raise OSError("copied config does not match the original")
			logHandler.log.info(f"Listen: moved config from {legacyPath} to {newPath}")
		else:
			logHandler.log.info(f"Listen: config already present at {newPath}, discarding {legacyPath}")
		os.remove(legacyPath)
	except OSError as e:
		logHandler.log.error(f"Listen: config migration failed, old file kept at {legacyPath}: {e}")
		return False
	return True


def loadConfig():
	configPath = getConfigPath()
	logHandler.log.info(f"Listen: config path resolved to {configPath}")
	try:
		os.makedirs(getConfigDir(), exist_ok=True)
	except OSError as e:
		logHandler.log.error(f"Listen: could not create {getConfigDir()}: {e}")

	wasMigrated = migrateLegacyConfig()
	loadedData = _readJsonDict(configPath)
	isNewFile = loadedData is None
	data = getDefaultData() if isNewFile else loadedData
	for key, defaultValue in getDefaultData().items():
		if not isinstance(data.get(key), type(defaultValue)):
			data[key] = defaultValue

	installedVersion = getInstalledVersion()
	storedVersion = data.get(VERSION_KEY)
	versionChanged = bool(installedVersion) and storedVersion != installedVersion
	if versionChanged:
		if storedVersion:
			logHandler.log.info(f"Listen: add-on updated from {storedVersion} to {installedVersion}")
		else:
			logHandler.log.info(f"Listen: add-on version recorded as {installedVersion}")
		data[VERSION_KEY] = installedVersion

	if isNewFile or wasMigrated or versionChanged:
		saveConfig(data)
	return data


def saveConfig(data):
	try:
		os.makedirs(getConfigDir(), exist_ok=True)
		writeJsonAtomic(getConfigPath(), data)
	except (OSError, TypeError, ValueError) as e:
		logHandler.log.debug(f"Listen: Failed to save config: {e}")
