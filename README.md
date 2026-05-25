# VNSdroid

VNSdroid is a lightweight, Python and Kivy-based VNDS (Visual Novel Script) interpreter optimized specifically for Android devices. 

The project addresses modern mobile hardware requirements, allowing legacy Nintendo DS visual novel ports to run smoothly on newer Android versions where older or unmaintained VNDS interpreters fail due to target API compatibility issues.

---

## Technical Features

* **Dynamic Device Orientation Control:** Automatially forces Portrait mode for navigating game lists and system settings, and locks into Landscape mode seamlessly upon executing game scripts.
* **State Persistence Management:** Built-in multi-slot Save/Load mechanism tracking script execution pointers, variable states, audio triggers, and local visual assets.
* **Resource Optimization:** Clean, decoupled design utilizing Kivy's asynchronous property binding for lightweight resource overhead and efficient touch scaling.
* **Directory Fallback Structure:** Handles standard path verification and localized parsing for game assets, with case-insensitivity safeguards built for mobile directory layouts.

---

## Prerequisites

To install and run this environment locally on a mobile device, ensure you have:
* An Android hardware platform.
* The **Pydroid 3** IDE app wrapper installed from the Google Play Store.
* An active network connection during initial provisioning to pull down dependency requirements.

---

## Installation & Launch Sequence

### 1. Initialize Pydroid 3
Install and launch **Pydroid 3** on your target device.

### 2. Extract Project Source
Download the latest compressed build asset (`VNSdroid.zip`) from the Releases tab and extract its directory contents into an accessible internal storage path.

### 3. Build Dependencies
Launch the Pydroid 3 side-drawer menu, select the native terminal emulator window, and install the required UI layout framework via pip:
```bash
 pip install kivy
