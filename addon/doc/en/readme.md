![NVDA Logo](https://www.nvaccess.org/files/nvda/documentation/userGuide/images/nvda.ico)

# Listen

Control background audio from anywhere. Auto-hides when you switch tasks, returns when you're back.

**author:** chai chaimee

**url:** https://github.com/chaichaimee/Listen

## Introduction

Listen lets you play an audio file straight from File Explorer and control it with simple single keys, without opening a media player. Select an audio file, press one hotkey, and the file starts playing while you keep working.

While Listen Mode is active, ordinary keys such as Space, the arrow keys, Page Up and Page Down become playback controls. When you switch to another window, the controls hide automatically so your keyboard behaves normally again. When you return to the window where you started, the controls come back and the audio resumes if it was stopped.

Listen remembers where you stopped in each file, your volume level, and your bookmarks, so you can continue exactly where you left off.

**Supported formats:** MP3, WAV, WMA, M4A, FLAC, AAC, OGG, OPUS, MID, MIDI

## Hot Keys

**ALT+Windows+L**

- Single Tap : Open Listen Mode
- Double Tap : Close Listen Mode

### Layer Mode Keys

These keys work only while Listen Mode is active.

**Playback**

- Space or C : Play / Pause
- Right Arrow : Forward 10 seconds
- Left Arrow : Back 10 seconds
- X : Restart the current file from the beginning
- E : Jump to the last 10 seconds of the file
- Up Arrow : Previous audio file in the folder
- Down Arrow : Next audio file in the folder
- Escape or Q : Hide Listen Mode (audio keeps playing)

**Volume**

- Page Up : Volume up
- Page Down : Volume down

**Time Information**

- W : Current position
- R : Remaining time
- T : Total duration

**Bookmarks**

- B : Add a bookmark at the current position
- Ctrl+B : Go to the next bookmark
- Shift+B : Go to the previous bookmark

**Jump by Percentage**

- 1 to 9 : Jump to 10% to 90% of the file (1 = 10%, 2 = 20%, and so on up to 9 = 90%)

**History**

- Z : Clear all saved positions and bookmarks

## Features

### Start Listening from File Explorer

Listen works on the audio file that is currently focused in a File Explorer window.

1. In File Explorer, move focus to a supported audio file.
2. Press ALT+Windows+L once.
3. You hear a beep and NVDA says "Listen Mode Active". The file starts playing.
4. If the focused item is not a supported audio file, NVDA says "Select Audio File". If the file cannot be opened, NVDA says "Error loading file".

### Auto Hide and Auto Return

Listen Mode is tied to the File Explorer window where you started it. When you switch to a different window, a low beep sounds, NVDA says "Listen Mode Hidden", and the layer keys are released so every key works normally in your other application. The audio is not interrupted.

When you come back to the original window, a beep sounds, NVDA says "Listen Mode Active", and the layer keys are available again. If the audio had stopped, it starts playing again.

Pressing ALT+Windows+L once while Listen Mode is hidden brings it back manually. Pressing it once while Listen Mode is already active plays a short confirmation beep.

### Hide Without Stopping

Press Escape or Q to hide Listen Mode while the audio keeps playing. This is useful when you want to type or use Explorer normally without losing your music. Press ALT+Windows+L once to bring the controls back. When Listen Mode is not in use, the Q key behaves as usual.

### Close Listen Mode Completely

Press ALT+Windows+L twice. The playback position, bookmarks, and volume are saved, the file is closed, and NVDA says "Permanently Stopped". Listen Mode will not return until you start it again from a new audio file.

### Resume Where You Left Off

Each time a file is stopped, closed, or you move to another file, Listen saves its playback position. The next time you open that same file, playback continues from the saved position instead of the beginning.

Example: You listen to a lecture until 25:10 and close Listen Mode. The next day you select the same file and press ALT+Windows+L. The lecture continues from 25:10.

### Browse Files in the Folder

Press Down Arrow for the next audio file or Up Arrow for the previous one. Listen looks at the folder of the current file, lists the supported audio files in alphabetical order, and plays the neighbouring file. NVDA announces the file name. After the last file it wraps to the first, and from the first file going back it wraps to the last. If the folder has no audio files, NVDA says "No audio files in folder".

### Bookmarks

You can mark important moments in a file and jump between them later. Bookmarks are saved separately for every file.

1. While the file is playing, press B at the moment you want to remember.
2. A high beep confirms the first bookmark. When the file already has bookmarks, you hear two beeps in a row.
3. Repeat for any other moments. Bookmarks are kept in time order.
4. Press Ctrl+B to jump to the next bookmark, or Shift+B to jump to the previous one. A beep confirms each jump.
5. If there is no bookmark in that direction, a low beep sounds.

A bookmark is not added if another bookmark already exists within half a second of the current position. In that case you hear a single short beep instead.

### Jump by Percentage

Keys 1 to 9 move playback to 10%, 20%, up to 90% of the total length of the file and NVDA announces the percentage.

Example: Press 5 to jump to the middle of the file. NVDA says "50 percent".

### Time Announcements

Press W for the current position, R for the remaining time, and T for the total duration. Times are spoken as minutes and seconds, or as hours, minutes, and seconds for longer files.

### Volume

Page Up and Page Down change the volume in small steps between 0 and 100. The default volume is 40, and your last volume level is remembered the next time you use Listen.

### Clear History

Press Z to delete every saved playback position and bookmark for all files. NVDA says "History Cleared".

### Saved Settings

Your volume, playback positions, and bookmarks are stored in the file listen.json inside the folder ChaiChaimee\Listen in your NVDA user configuration folder. If you used an older version, your existing settings are moved to this new location automatically the first time the updated add-on loads.

## Support Me

If this tool has made your life easier, consider fueling the next update with a small donation.

[![Support me](https://img.shields.io/badge/Donate-Support%20Me-blue?style=for-the-badge&logo=stripe)](https://buy.stripe.com/dRm9AU1xQ3Ds22N6VK1VK01)

Your support means the world. Let's build something great together

© 2026 Chai Chaimee NVDA Add-on Released under GNU GPL
