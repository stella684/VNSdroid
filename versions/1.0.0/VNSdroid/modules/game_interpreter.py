import os
import zipfile
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image as KivyImage
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.app import App
from kivy.properties import StringProperty, BooleanProperty, ListProperty, NumericProperty
from kivy.logger import Logger
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
from kivy.core.window import Window

from modules.saveload import SaveLoadPopup

class VNInterpreter(BoxLayout):
    current_game_folder = StringProperty("")
    dialogue_text = StringProperty("")
    char_name = StringProperty("")
    bg_source = StringProperty("")
    
    is_choosing = BooleanProperty(False)
    choices = ListProperty([])
    auto_mode = BooleanProperty(False)
    
    auto_speed = NumericProperty(2.0)
    bg_keep_ratio = BooleanProperty(True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.script_lines = []
        self.current_line_idx = 0
        self.current_script_name = "main.scr"
        self.variables = {"selected": 0}
        self.current_music = None
        self.current_sound = None
        self.auto_event = None
        self.current_bg_name = ""

    def load_settings(self):
        config_file = './assets/saves/setting_configure.txt'
        self.auto_speed = 2.0
        self.bg_keep_ratio = True
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if '=' in line:
                            key, val = line.strip().split('=', 1)
                            if key == 'auto_speed':
                                self.auto_speed = float(val)
                            elif key == 'display_mode':
                                self.bg_keep_ratio = (val == "Fixed")
            except Exception as e:
                Logger.error(f"Interpreter: Settings file reading issue: {e}")

    def get_asset(self, category, filename):
        if filename == "~" or not filename: return ""
        normal_path = os.path.join(self.current_game_folder, category, filename)
        if os.path.exists(normal_path): return normal_path
            
        zip_path = os.path.join(self.current_game_folder, f"{category}.zip")
        if os.path.exists(zip_path):
            cache_dir = os.path.join(self.current_game_folder, '.cache', category)
            if not os.path.exists(cache_dir): os.makedirs(cache_dir)
            try:
                with zipfile.ZipFile(zip_path, 'r') as z:
                    for info in z.infolist():
                        if info.filename.endswith(filename):
                            safe_name = os.path.basename(info.filename)
                            cached_file = os.path.join(cache_dir, safe_name)
                            if not os.path.exists(cached_file):
                                with z.open(info) as source, open(cached_file, 'wb') as target:
                                    target.write(source.read())
                            return cached_file
            except Exception as e: Logger.error(f"Interpreter: Zip extraction failed: {e}")
                
        fallback = os.path.join(self.current_game_folder, filename)
        if os.path.exists(fallback): return fallback
        return ""

    def start_story(self, game_folder_path):
        self.load_settings()
        self.current_game_folder = game_folder_path
        
        if self.auto_event: self.auto_event.cancel()
        if self.current_music: self.current_music.stop()
        if self.current_sound: self.current_sound.stop()
        if 'sprite_layer' in self.ids: self.ids.sprite_layer.clear_widgets()
        
        main_script = self.get_asset('script', 'main.scr') 
        if main_script and os.path.exists(main_script):
            self.load_script(main_script)
            self.run_next_command()
        else:
            self.dialogue_text = f"Error: main.scr not found."

    def load_script(self, path):
        self.current_script_name = os.path.basename(path)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.script_lines = [line.strip() for line in f.readlines() if line.strip()]
            self.current_line_idx = 0
        except Exception as e: Logger.error(f"Interpreter Error: {e}")

    def run_next_command(self):
        if self.current_line_idx >= len(self.script_lines): return
        line = self.script_lines[self.current_line_idx]
        self.current_line_idx += 1
        parts = line.split(' ', 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "text": 
            self.handle_text(args)
            if self.auto_mode: self.trigger_auto()
        elif cmd in ["bgload", "bg_load"]:
            if 'sprite_layer' in self.ids: self.ids.sprite_layer.clear_widgets()
            self.current_bg_name = args
            self.bg_source = self.get_asset('background', args)
            self.run_next_command()
        elif cmd == "setimg": 
            self.handle_setimg(args)
        elif cmd == "delay":
            try:
                p = int(args) / 1000.0 
                Clock.schedule_once(lambda dt: self.run_next_command(), p)
            except: self.run_next_command()
        elif cmd == "music":
            self.play_audio(args, True)
            self.run_next_command()
        elif cmd == "sound":
            self.play_audio(args, False)
            self.run_next_command()
        elif cmd == "choice": 
            self.handle_choice(args)
            if self.auto_event: self.auto_event.cancel()
        elif cmd == "jump":
            new_path = self.get_asset('script', args)
            if new_path: self.load_script(new_path)
            self.run_next_command()
        else: self.run_next_command()

    def handle_text(self, raw_text):
        text = raw_text.strip().strip('"').strip()
        if text in ["~", "!"]: self.char_name, self.dialogue_text = "", ""
        elif text.startswith("@"): self.char_name, self.dialogue_text = " ", text[1:]
        elif ":" in text:
            name, speech = text.split(":", 1)
            self.char_name, self.dialogue_text = name.strip(), speech.strip()
        else: self.char_name, self.dialogue_text = "", text

    def handle_setimg(self, args):
        if args != "~" and 'sprite_layer' in self.ids:
            p = args.split()
            if len(p) >= 1:
                filepath = self.get_asset('foreground', p[0])
                if filepath and os.path.exists(filepath):
                    img = KivyImage(source=filepath, allow_stretch=True, keep_ratio=True)
                    img.size_hint = (None, 0.95) 
                    def scale_img(instance, *args_list):
                        if instance.texture_size[1] > 0: instance.width = instance.height * (instance.texture_size[0] / instance.texture_size[1])
                    img.bind(height=scale_img, texture_size=scale_img)
                    if len(p) >= 3:
                        x_coord = float(p[1])
                        if x_coord < 400:
                            img.pos_hint = {'x': 0.05, 'y': 0.0}
                            img.color = [1, 1, 1, 1]
                        else:
                            img.pos_hint = {'right': 0.95, 'y': 0.0}
                            img.color = [1, 1, 1, 0.6]
                    self.ids.sprite_layer.add_widget(img)
        self.run_next_command()

    def handle_choice(self, args):
        self.choices = args.split('|')
        self.is_choosing = True

    def select_choice(self, val):
        self.variables["selected"] = val
        self.is_choosing = False
        self.run_next_command()

    def play_audio(self, raw_args, is_music=True):
        target = self.current_music if is_music else self.current_sound
        if target: target.stop()
        if raw_args == "~": return
        parts = raw_args.split()
        filepath = self.get_asset('sound', parts[0])
        if filepath and os.path.exists(filepath):
            snd = SoundLoader.load(filepath)
            if snd:
                snd.loop = (is_music or (len(parts) > 1 and parts[1] == "-1"))
                snd.play()
                if is_music: self.current_music = snd
                else: self.current_sound = snd

    def next_line(self):
        if self.auto_event: self.auto_event.cancel() 
        if not self.is_choosing: self.run_next_command()

    def trigger_auto(self):
        if self.auto_event: self.auto_event.cancel()
        if not self.is_choosing and self.dialogue_text:
            self.auto_event = Clock.schedule_once(lambda dt: self.next_line(), self.auto_speed)

    def toggle_auto(self):
        self.auto_mode = not self.auto_mode
        if self.auto_mode: self.trigger_auto()
        elif self.auto_event: self.auto_event.cancel()

    def toggle_fullscreen(self):
        Window.fullscreen = 'auto' if Window.fullscreen != 'auto' else False

    def open_save_ui(self):
        SaveLoadPopup(self, mode='save').open()

    def open_load_ui(self):
        SaveLoadPopup(self, mode='load').open()

    def exit_to_menu(self):
        content = BoxLayout(orientation='vertical', padding='15dp', spacing='15dp')
        msg = Label(
            text="Are you sure you want to return to the menu?\nUnsaved progress will be lost.", 
            halign='center', 
            valign='middle', 
            font_size='16sp',
            font_name='./assets/jpfont.ttf'
        )
        msg.bind(size=msg.setter('text_size'))
        content.add_widget(msg)
        
        btn_layout = BoxLayout(orientation='horizontal', spacing='10dp', size_hint_y=None, height='45dp')
        cancel_btn = Button(text="Cancel", background_color=(0.25, 0.25, 0.28, 1))
        confirm_btn = Button(text="Yes", background_color=(0.8, 0.2, 0.2, 1))
        
        btn_layout.add_widget(cancel_btn)
        btn_layout.add_widget(confirm_btn)
        content.add_widget(btn_layout)

        popup = Popup(title="Return to Menu", content=content, size_hint=(None, None), size=('320dp', '180dp'), auto_dismiss=True, background_color=(0.14, 0.14, 0.16, 1), title_align='center', separator_color=(1, 1, 1, 1))
        
        cancel_btn.bind(on_release=popup.dismiss)
        confirm_btn.bind(on_release=lambda btn: self.confirm_exit(popup))
        popup.open()

    def confirm_exit(self, popup):
        popup.dismiss()
        if self.auto_event: self.auto_event.cancel()
        if self.current_music: self.current_music.stop()
        if self.current_sound: self.current_sound.stop()
        App.get_running_app().root.current = 'menu_screen'

    def get_save_state(self):
        return {
            'game': self.current_game_folder,
            'script': getattr(self, 'current_script_name', 'main.scr'),
            'line': self.current_line_idx - 1, 
            'bg': self.current_bg_name, 
            'vars': self.variables,
            'char_name': self.char_name,
            'dialogue_text': self.dialogue_text
        }

    def load_save_state(self, data):
        self.load_settings()  
        
        if self.auto_event:
            self.auto_event.cancel()
            self.auto_event = None
        if self.current_music: self.current_music.stop()
        if self.current_sound: self.current_sound.stop()

        self.current_game_folder = data.get('game', '')
        self.variables = data.get('vars', {})
        self.char_name = data.get('char_name', '')
        self.dialogue_text = data.get('dialogue_text', '')
        
        self.current_bg_name = data.get('bg', '')
        if self.current_bg_name:
            self.bg_source = self.get_asset('background', self.current_bg_name)
        else:
            self.bg_source = ""
        
        if 'sprite_layer' in self.ids: self.ids.sprite_layer.clear_widgets()

        script_name = data.get('script', 'main.scr')
        target_script = self.get_asset('script', script_name)
        
        if target_script and os.path.exists(target_script):
            self.load_script(target_script)
        else:
            Logger.error(f"Interpreter: Missing Script {script_name}")
            return
        
        self.current_line_idx = max(0, data.get('line', 0))

        for i in range(self.current_line_idx - 1, -1, -1):
            if i < len(self.script_lines):
                line = self.script_lines[i].strip()
                parts = line.split(' ', 1)
                cmd = parts[0].lower()
                if cmd == "music":
                    args = parts[1] if len(parts) > 1 else ""
                    self.play_audio(args, True)
                    break
        
        self.run_next_command()
