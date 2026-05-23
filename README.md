# VNSdroid

VNSdroid is a Visual Novel interpreter project created by **stella684**.

It allows you to run **Nintendo DS Visual Novel ports** on modern Android devices using Python and Kivy.

This project was created because many older VNDS interpreters no longer work properly on newer phones.

---

# Features

- Run VNDS/Nintendo DS visual novels on Android
- Modern device support
- Lightweight and simple UI
- Built with Python + Kivy
- Easy setup process

---

# Requirements

Before using VNSdroid, make sure you have:

- Android device
- Pydroid 3 installed
- Internet connection

---

# Installation

## 1. Install Pydroid 3

Download **Pydroid 3** from the Play Store.

---

## 2. Download VNSdroid

Go to the **Releases** section of this repository and download the latest VNSdroid `.zip` file.

Extract the zip anywhere in your internal storage.

---

## 3. Install Kivy

Open Pydroid 3.

Open the sidebar → Terminal

Run:

```bash
pip install kivy
```

Wait for installation to finish.

---

## 4. Launch VNSdroid

Inside the extracted folder, you may find different versions. Choose the version of VNSdroid you like, then open the VNSdroid folder and open:

```text
main.py
```

Run `main.py` using Pydroid 3.

---

# Game Structure Example

```text
games/
└── gamename/
    ├── background.zip
    ├── foreground.zip
    ├── sound.zip
    └── script.zip/
        ├── main.scr
        ├── endings.scr
        └── debug.scr
```

---

# Notes

- More help can be found inside the Settings page
- Some games may require properly formatted VNDS assets
- Performance may vary depending on your device

---

# Credits

Created by **stella684**

Built using Python and Kivy.

---

# Copyright

Copyright © 2026 stella684  
All rights reserved.
