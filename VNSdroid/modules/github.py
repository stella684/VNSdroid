import os
import threading
import zipfile
import shutil
import urllib.request
import socket
import re
import webbrowser
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.app import App
from kivy.clock import Clock
from kivy.logger import Logger

GITHUB_USER = "stella684"
GITHUB_REPO = "VNSdroid"
GITHUB_BRANCH = "main"
SUBFOLDER = "VNSdroid"

RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{SUBFOLDER}"
ZIP_URL = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/archive/refs/heads/{GITHUB_BRANCH}.zip"
README_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/README.md"
VERSION_URL = f"{RAW_BASE}/version.txt"

APP_ROOT = os.path.abspath(".")


def is_online(host="8.8.8.8", port=53, timeout=3):
    """Quick TCP check — no HTTP needed, very fast."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except (socket.error, OSError):
        return False


class GithubMenu(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.remote_version = None
        self.local_version = self._read_local_version()
        Clock.schedule_once(lambda dt: self._load_readme(), 0.3)

    def _read_local_version(self):
        vpath = os.path.join(APP_ROOT, 'version.txt')
        if os.path.exists(vpath):
            try:
                with open(vpath, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception:
                pass
        return "unknown"


    def _load_readme(self):
        if 'readme_label' not in self.ids:
            return
        self.ids.readme_label.text = "Loading README..."

        def fetch():
            if not is_online():
                Clock.schedule_once(lambda dt: self._set_readme(
                    "[color=888888]No internet connection.\nConnect to Wi-Fi or mobile data to load the README.[/color]"
                ))
                return
            try:
                with urllib.request.urlopen(README_URL, timeout=10) as r:
                    text = r.read().decode('utf-8')
            except Exception as e:
                text = f"[color=888888]Could not load README.\n({e})[/color]"
            Clock.schedule_once(lambda dt: self._set_readme(text))

        threading.Thread(target=fetch, daemon=True).start()

    def _parse_markdown(self, text):

        text = text.replace('[', '&bl;').replace(']', '&br;')
        
        text = re.sub(r'(?m)^# (.*?)$', r'[size=26sp][b][color=ffffff]\1[/color][/b][/size]', text)
        text = re.sub(r'(?m)^## (.*?)$', r'[size=22sp][b][color=eeeeee]\1[/color][/b][/size]', text)
        text = re.sub(r'(?m)^### (.*?)$', r'[size=18sp][b][color=dddddd]\1[/color][/b][/size]', text)
        
        text = re.sub(r'\*\*(.*?)\*\*', r'[b]\1[/b]', text)
        text = re.sub(r'\*(.*?)\*', r'[i]\1[/i]', text)
        text = re.sub(r'_(.*?)_', r'[i]\1[/i]', text)
        
        text = re.sub(r'`(.*?)`', r'[color=c9d1d9]\1[/color]', text)
        
        text = re.sub(r'&bl;(.*?)&br;\((.*?)\)', r'[color=58a6ff][ref=\2]\1[/ref][/color]', text)
        
        text = re.sub(r'(?m)^[-*]\s+(.*?)$', r'  • \1', text)
        
        text = re.sub(r'(?m)^>\s+(.*?)$', r'[color=8b949e]    | \1[/color]', text)
        
        return text

    def open_url(self, instance, url):
        try:
            webbrowser.open(url)
        except Exception as e:
            Logger.error(f"GithubMenu: Failed to open link - {e}")

    def _set_readme(self, text):
        if 'readme_label' in self.ids:
            parsed_text = self._parse_markdown(text)
            self.ids.readme_label.markup = True
            self.ids.readme_label.text = parsed_text

    def check_update(self):
        if 'update_btn' in self.ids:
            self.ids.update_btn.text = "Checking..."
            self.ids.update_btn.disabled = True

        def fetch():
            if not is_online():
                Clock.schedule_once(lambda dt: self._on_offline())
                return
            try:
                with urllib.request.urlopen(VERSION_URL, timeout=10) as r:
                    remote = r.read().decode('utf-8').strip()
                Clock.schedule_once(lambda dt: self._on_version_fetched(remote))
            except Exception as e:
                Clock.schedule_once(lambda dt: self._on_check_error(str(e)))

        threading.Thread(target=fetch, daemon=True).start()

    def _on_offline(self):
        self._reset_update_btn()
        self._show_dialog(
            "No Internet Connection",
            "You're currently offline.\n\nPlease connect to Wi-Fi or mobile data and try again.",
            [("OK", None)]
        )

    def _on_check_error(self, msg):
        self._reset_update_btn()
        self._show_dialog(
            "Connection Error",
            f"Could not reach GitHub.\n\n{msg}",
            [("OK", None)]
        )

    def _on_version_fetched(self, remote):
        self._reset_update_btn()
        self.remote_version = remote
        local = self.local_version

        if remote == local:
            self._show_dialog(
                "Up to Date",
                f"You're already on the latest version.\n\nCurrent: [b]{local}[/b]",
                [("OK", None)]
            )
        else:
            self._show_dialog(
                "Update Available",
                f"A new version is available!\n\n"
                f"[b]{local}[/b]  →  [b]{remote}[/b]\n\n"
                f"Would you like to update now?",
                [("Cancel", None), ("Update", self._start_update)]
            )

    def _reset_update_btn(self):
        if 'update_btn' in self.ids:
            self.ids.update_btn.text = "Check for Updates"
            self.ids.update_btn.disabled = False

    def _start_update(self):
        content = BoxLayout(orientation='vertical', padding='20dp', spacing='15dp')

        self._progress_label = Label(
            text="Downloading update...",
            font_name='./assets/jpfont.ttf',
            font_size='15sp',
            halign='center',
            valign='middle',
            color=(0.9, 0.9, 0.9, 1)
        )
        self._progress_label.bind(size=self._progress_label.setter('text_size'))
        self._progress_bar = ProgressBar(max=100, value=0, size_hint_y=None, height='20dp')

        content.add_widget(self._progress_label)
        content.add_widget(self._progress_bar)

        self._progress_popup = Popup(
            title="Installing Update",
            content=content,
            size_hint=(0.8, None),
            height='200dp',
            auto_dismiss=False,
            background_color=(0.08, 0.08, 0.08, 0.98),
            title_font='./assets/jpfont.ttf',
            title_align='center',
            separator_color=(0.3, 0.3, 0.3, 1)
        )
        self._progress_popup.open()

        threading.Thread(target=self._download_and_install, daemon=True).start()

    def _set_progress(self, val, msg):
        def _do(dt):
            if hasattr(self, '_progress_bar'):
                self._progress_bar.value = val
            if hasattr(self, '_progress_label'):
                self._progress_label.text = msg
        Clock.schedule_once(_do)

    def _download_and_install(self):

        if not is_online():
            Clock.schedule_once(lambda dt: self._on_update_offline())
            return

        tmp_zip = os.path.join(APP_ROOT, '_update_tmp.zip')
        tmp_dir = os.path.join(APP_ROOT, '_update_extracted')

        try:
            self._set_progress(5, "Connecting to GitHub...")

            req = urllib.request.Request(ZIP_URL, headers={'User-Agent': 'VNSdroid-Updater'})
            with urllib.request.urlopen(req, timeout=60) as r:
                total = int(r.headers.get('Content-Length', 0))
                downloaded = 0
                with open(tmp_zip, 'wb') as f:
                    while True:
                        buf = r.read(8192)
                        if not buf:
                            break
                        f.write(buf)
                        downloaded += len(buf)
                        if total > 0:
                            pct = int((downloaded / total) * 60) + 5
                            self._set_progress(pct, f"Downloading... {downloaded // 1024} KB")

            self._set_progress(65, "Extracting files...")

            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
            os.makedirs(tmp_dir)

            with zipfile.ZipFile(tmp_zip, 'r') as z:
                z.extractall(tmp_dir)

            self._set_progress(75, "Locating app files...")

            source_root = None
            for root, dirs, files in os.walk(tmp_dir):
                if 'main.py' in files:
                    source_root = root
                    break

            if not source_root:
                raise FileNotFoundError(
                    "Could not find main.py in the downloaded zip.\n"
                    "The release layout may have changed."
                )

            self._set_progress(80, "Installing files...")

            items = os.listdir(source_root)
            total_items = max(len(items), 1)

            for i, item in enumerate(items):
                src = os.path.join(source_root, item)
                dst = os.path.join(APP_ROOT, item)
                if os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
                pct = 80 + int((i + 1) / total_items * 15)
                self._set_progress(pct, f"Installing... ({i+1}/{total_items})")

            self._set_progress(97, "Cleaning up...")
            os.remove(tmp_zip)
            shutil.rmtree(tmp_dir)

            self._set_progress(100, "Done!")
            self.local_version = self.remote_version
            Clock.schedule_once(lambda dt: self._on_install_success())

        except Exception as e:
            Logger.error(f"Updater: {e}")
            try:
                if os.path.exists(tmp_zip):
                    os.remove(tmp_zip)
                if os.path.exists(tmp_dir):
                    shutil.rmtree(tmp_dir)
            except Exception:
                pass
            Clock.schedule_once(lambda dt: self._on_install_error(str(e)))

    def _on_update_offline(self):
        if hasattr(self, '_progress_popup'):
            self._progress_popup.dismiss()
        self._show_dialog(
            "No Internet Connection",
            "Lost connection before the download could start.\n\nPlease reconnect and try again.",
            [("OK", None)]
        )

    def _on_install_success(self):
        if hasattr(self, '_progress_popup'):
            self._progress_popup.dismiss()
        self._show_dialog(
            "Update Complete",
            f"Successfully updated to [b]{self.remote_version}[/b]!\n\n"
            "Please restart the app to apply changes.",
            [("Restart", self._restart_app), ("Later", None)]
        )

    def _on_install_error(self, msg):
        if hasattr(self, '_progress_popup'):
            self._progress_popup.dismiss()
        self._show_dialog(
            "Update Failed",
            f"Something went wrong during installation.\n\n"
            f"[color=FF6B6B]{msg}[/color]\n\n"
            "Your files have not been modified. Please try again or update manually.",
            [("OK", None)]
        )

    def _restart_app(self):
        import sys
        try:
            App.get_running_app().stop()
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            self._show_dialog(
                "Restart Failed",
                f"Could not restart automatically.\nPlease close and reopen the app.\n\n({e})",
                [("OK", None)]
            )

    def _show_dialog(self, title, message, buttons):
        from kivy.uix.button import Button
        from kivy.graphics import Color, RoundedRectangle

        content = BoxLayout(orientation='vertical', padding='15dp', spacing='15dp')

        msg = Label(
            text=message,
            markup=True,
            font_name='./assets/jpfont.ttf',
            font_size='15sp',
            halign='center',
            valign='middle',
            color=(0.92, 0.92, 0.92, 1)
        )
        msg.bind(size=msg.setter('text_size'))
        content.add_widget(msg)

        btn_row = BoxLayout(orientation='horizontal', spacing='10dp', size_hint_y=None, height='45dp')

        popup = Popup(
            title=title,
            content=content,
            size_hint=(0.82, None),
            height='220dp',
            auto_dismiss=True,
            background_color=(0.09, 0.09, 0.10, 0.97),
            title_font='./assets/jpfont.ttf',
            title_align='center',
            separator_color=(0.3, 0.3, 0.3, 1)
        )

        for label, cb in buttons:
            is_action = cb is not None
            btn = Button(
                text=label,
                font_name='./assets/jpfont.ttf',
                background_normal='',
                background_color=(0, 0, 0, 0)
            )
            bg_color = (0.18, 0.45, 0.18, 1) if is_action else (0.22, 0.22, 0.25, 1)

            with btn.canvas.before:
                _c = Color(*bg_color)
                _r = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[12])

            def _update_rect(instance, value, _r=_r):
                _r.pos = instance.pos
                _r.size = instance.size

            btn.bind(pos=_update_rect, size=_update_rect)

            def make_cb(popup, cb):
                def _on_release(instance):
                    popup.dismiss()
                    if cb:
                        cb()
                return _on_release

            btn.bind(on_release=make_cb(popup, cb))
            btn_row.add_widget(btn)

        content.add_widget(btn_row)
        popup.open()

    def go_home(self):
        App.get_running_app().root.current = 'menu_screen'

    def go_settings(self):
        App.get_running_app().root.current = 'settings_screen'

