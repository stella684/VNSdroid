import os
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.app import App
from kivy.properties import StringProperty, NumericProperty

CONFIG_FILE = './assets/saves/setting_configure.txt'

class SettingsMenu(BoxLayout):
    app_version = StringProperty("")
    auto_speed = NumericProperty(2.0)
    display_mode = StringProperty("Fixed")
    master_vol = NumericProperty(1.0)
    bgm_vol = NumericProperty(1.0)
    sfx_vol = NumericProperty(1.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.load_version()
        self.load_config()

    def load_version(self):
        version_file = './version.txt'
        if os.path.exists(version_file):
            try:
                with open(version_file, 'r', encoding='utf-8') as f:
                    self.app_version = f.read().strip()
            except Exception:
                self.app_version = "v?.?"
        else:
            self.app_version = "v?.?"

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        if '=' in line:
                            key, val = line.strip().split('=', 1)
                            if key == 'auto_speed':
                                self.auto_speed = float(val)
                            elif key == 'display_mode':
                                self.display_mode = val
                            elif key == 'master_vol':
                                self.master_vol = float(val)
                            elif key == 'bgm_vol':
                                self.bgm_vol = float(val)
                            elif key == 'sfx_vol':
                                self.sfx_vol = float(val)
            except Exception:
                pass
        else:
            self.save_config()

    def save_config(self):
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write(f"auto_speed={self.auto_speed}\n")
                f.write(f"display_mode={self.display_mode}\n")
                f.write(f"master_vol={self.master_vol}\n")
                f.write(f"bgm_vol={self.bgm_vol}\n")
                f.write(f"sfx_vol={self.sfx_vol}\n")
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def update_auto_speed(self, text_val):
        if not text_val:
            return
        try:
            self.auto_speed = float(text_val)
            self.save_config()
        except ValueError:
            pass

    def toggle_display_mode(self):
        self.display_mode = "Full" if self.display_mode == "Fixed" else "Fixed"
        self.save_config()

    def update_volume(self, vol_type, value):
        if vol_type == 'master':
            self.master_vol = value
        elif vol_type == 'bgm':
            self.bgm_vol = value
        elif vol_type == 'sfx':
            self.sfx_vol = value
        self.save_config()

    def open_text_popup(self, title, filename):
        filepath = os.path.join('./assets/txts', filename)
        pages = ["File not found or empty."]
        
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                raw_blocks = content.split('\n\n')
                filtered = [b.strip() for b in raw_blocks if b.strip()]
                if filtered:
                    pages = filtered
            except Exception as e:
                pages = [f"Error reading file: {e}"]

        current_page_idx = [0]
        content_box = BoxLayout(orientation='vertical', padding='15dp', spacing='15dp')
        
        text_label = Label(
            text=pages[0],
            font_name='./assets/jpfont.ttf',
            font_size='15sp',
            halign='center',
            valign='middle',
            color=(0.9, 0.9, 0.9, 1)
        )
        text_label.bind(size=text_label.setter('text_size'))
        content_box.add_widget(text_label)

        nav_layout = BoxLayout(orientation='horizontal', spacing='10dp', size_hint_y=None, height='45dp')
        back_btn = Button(text="< Back", font_name='./assets/jpfont.ttf', background_normal='', background_color=(0.15, 0.15, 0.15, 1), disabled=True)
        next_btn = Button(text="Next >" if len(pages) > 1 else "Close", font_name='./assets/jpfont.ttf', background_normal='', background_color=(0.2, 0.2, 0.22, 1))

        nav_layout.add_widget(back_btn)
        nav_layout.add_widget(next_btn)
        content_box.add_widget(nav_layout)

        popup = Popup(
            title=title,
            content=content_box,
            size_hint=(0.85, 0.6),
            auto_dismiss=True,
            background_color=(0.08, 0.08, 0.08, 0.98),
            title_align='center',
            separator_color=(0.3, 0.3, 0.3, 1)
        )

        def refresh_ui():
            text_label.text = pages[current_page_idx[0]]
            back_btn.disabled = (current_page_idx[0] == 0)
            if current_page_idx[0] == len(pages) - 1:
                next_btn.text = "Close"
            else:
                next_btn.text = "Next >"

        def on_next_release(instance):
            if current_page_idx[0] < len(pages) - 1:
                current_page_idx[0] += 1
                refresh_ui()
            else:
                popup.dismiss()

        def on_back_release(instance):
            if current_page_idx[0] > 0:
                current_page_idx[0] -= 1
                refresh_ui()

        next_btn.bind(on_release=on_next_release)
        back_btn.bind(on_release=on_back_release)
        
        popup.open()

    def go_home(self):
        App.get_running_app().root.current = 'menu_screen'
