# VNSdroid
a python &amp; kivy based VNDS interpreter made for Android devices
# VNSdroid

VNSdroid is a Visual Novel interpreter project created by **stella684**.  
It allows you to run **Nintendo DS Visual Novel ports** on modern Android devices.

This project was made because many old VNDS interpreters no longer work properly on newer phones.

---

# Features

- Run VNDS/Nintendo DS visual novels on Android
- Works on modern devices
- Lightweight and simple
- Built with Python + Kivy
- Beginner-friendly setup

---

# Requirements

Before installing VNSdroid, make sure you have:

- Android device
- Pydroid 3 installed
- Internet connection

---

# Installation Guide

## 1. Install Pydroid 3

Download **Pydroid 3** from the Play Store.

---

## 2. Create install.py

1. Open Pydroid 3
2. Press the folder icon
3. Click **Save As**
4. Choose internal storage
5. Create a folder
6. Create a file named:

```py
install.py
```

7. Paste the installer code into it from install.py inside repository
8. Save the file

---

## 3. Install Kivy

Open the Pydroid 3 sidebar → Terminal

Run:

```bash
pip install kivy
```

Wait for installation to finish.

---

## 4. Run Installer

1. Open `install.py`
2. Press Run
3. Select your VNSdroid version
4. Wait until installation completes

After installation, a new folder named:

```text
VNSdroid
```

will appear in the same directory.

---

## 5. Launch VNSdroid

Open:

```text
VNSdroid/main.py
```

Run `main.py` using Pydroid 3.

---

# Example Game Structure

```text
games/
└── gamename/
    ├── background.zip
    ├── foreground.zip
    ├── sound.zip
    └── scripts.zip/
        ├── main.scr
        ├── endings.scr
        └── debug.scr
```

---

# Notes

- More help can be found in the Settings page
- Some games may require properly formatted VNDS files
- Performance depends on your device

---

# Credits

Created by **stella684**

Built using Python and Kivy.

---

# Copyright

Copyright © 2026 stella684
All rights reserved.
