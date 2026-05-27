import os
import json
import zipfile
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image as KivyImage
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.app import App
from kivy.properties import StringProperty, BooleanProperty, ListProperty, NumericProperty
from kivy.logger import Logger
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.animation import Animation

from modules.saveload import SaveLoadPopup
from modules.script_engine import ScriptEngine 

class VNInterpreter(BoxLayout):
    current_game_folder = StringProperty("")
    dialogue_text = StringProperty("")
    char_name = StringProperty("")
    bg_source = StringProperty("")
    
    is_choosing = BooleanProperty(False)
    choices = ListProperty([])
    
    auto_mode = BooleanProperty(False)
    ui_hidden = BooleanProperty(False)
    drawer_open = BooleanProperty(False)
    
    auto_speed = NumericProperty(2.0)
    bg_keep_ratio = BooleanProperty(True)
    
    master_vol = NumericProperty(1.0)
    bgm_vol = NumericProperty(1.0)
    sfx_vol = NumericProperty(1.0)
    
    ui_opacity = NumericProperty(1.0)
    transition_opacity = NumericProperty(0.0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.engine = ScriptEngine() 
        self.current_music = None
        self.current_sound = None
        self.auto_event = None
        self.current_bg_name = ""
        self.dialogue_history = [] 
        
        self.active_sprites = {} 
        self.active_sprites_info = {}
        
        self.typewriter_event = None
        self.full_text = ""
        self.type_index = 0

    def load_settings(self):
        config_file = './assets/saves/setting_configure.txt'
        self.auto_speed = 2.0
        self.bg_keep_ratio = True
        self.master_vol = 1.0
        self.bgm_vol = 1.0
        self.sfx_vol = 1.0
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if '=' in line:
                            key, val = line.strip().split('=', 1)
                            if key == 'auto_speed': self.auto_speed = float(val)
                            elif key == 'display_mode': self.bg_keep_ratio = (val == "Fixed")
                            elif key == 'master_vol': self.master_vol = float(val)
                            elif key == 'bgm_vol': self.bgm_vol = float(val)
                            elif key == 'sfx_vol': self.sfx_vol = float(val)
            except Exception as e:
                Logger.error(f"Interpreter: Settings file reading issue: {e}")

    def _apply_custom_ui(self):
        if 'custom_ui_layer' not in self.ids or 'default_ui_layer' not in self.ids:
            return

        self.ids.custom_ui_layer.clear_widgets()
        custom_ui_path = os.path.join(self.current_game_folder, 'ui.kv')
        
        if os.path.exists(custom_ui_path):
            try:
                Builder.unload_file(custom_ui_path)
                custom_widget = Builder.load_file(custom_ui_path)
                self.ids.custom_ui_layer.add_widget(custom_widget)
                self.ids.default_ui_layer.opacity = 0
                self.ids.default_ui_layer.disabled = True
            except Exception as e:
                self.ids.default_ui_layer.opacity = 1
                self.ids.default_ui_layer.disabled = False
        else:
            self.ids.default_ui_layer.opacity = 1
            self.ids.default_ui_layer.disabled = False

    def get_asset(self, category, filename):
        if filename == "~" or not filename: return ""
        
        target_path = filename.replace('\\', '/')
        categories = [category]
        
        if '/' in target_path:
            prefix = target_path.split('/')[0]
            if prefix not in categories:
                categories.append(prefix)
                
        for cat in categories:
            normal_path = os.path.join(self.current_game_folder, cat, filename)
            if os.path.exists(normal_path): 
                return normal_path
                
            zip_path = os.path.join(self.current_game_folder, f"{cat}.zip")
            if os.path.exists(zip_path):
                cache_dir = os.path.join(self.current_game_folder, '.cache', cat)
                try:
                    with zipfile.ZipFile(zip_path, 'r') as z:
                        target_components = [p.lower() for p in target_path.strip('/').split('/')]
                        for info in z.infolist():
                            if info.filename.endswith('/') or info.file_size == 0:
                                continue
                            normalized_info = info.filename.replace('\\', '/').strip('/')
                            info_components = [p.lower() for p in normalized_info.split('/')]
                            
                            if len(info_components) >= len(target_components):
                                if info_components[-len(target_components):] == target_components:
                                    safe_cache_path = info.filename.replace('/', os.sep)
                                    cached_file = os.path.join(cache_dir, safe_cache_path)
                                    if not os.path.exists(cached_file) or os.path.getsize(cached_file) == 0:
                                        os.makedirs(os.path.dirname(cached_file), exist_ok=True)
                                        with z.open(info) as source, open(cached_file, 'wb') as target:
                                            target.write(source.read())
                                    return cached_file
                except Exception as e:
                    Logger.error(f"Interpreter: Zip extraction error: {e}")

        fallback = os.path.join(self.current_game_folder, filename)
        if os.path.exists(fallback): return fallback
        return ""

    def start_story(self, game_folder_path):
        self.load_settings()
        self.current_game_folder = game_folder_path
        self._apply_custom_ui()
        
        self.auto_mode = False
        self.ui_hidden = False
        self.drawer_open = False
        self.ui_opacity = 1.0
        
        if 'side_drawer' in self.ids:
            self.ids.side_drawer.pos_hint = {'x': 1.0, 'y': 0.0}

        if self.auto_event: self.auto_event.cancel()
        if self.typewriter_event: self.typewriter_event.cancel()
        if self.current_music: self.current_music.stop()
        if self.current_sound: self.current_sound.stop()
        
        if 'sprite_layer' in self.ids: self.ids.sprite_layer.clear_widgets()
        self.active_sprites.clear()
        self.active_sprites_info.clear()
        
        self.transition_opacity = 0.0
        self.engine.variables["voiced"] = 1  
        self.dialogue_history = []
        
        main_script = self.get_asset('script', 'main.scr') 
        if main_script and os.path.exists(main_script):
            self.engine.load_script(main_script)
            self.run_next_command()
        else:
            s04_script = self.get_asset('script', 's04.scr')
            if s04_script and os.path.exists(s04_script):
                self.engine.load_script(s04_script)
                self.run_next_command()
            else:
                self.dialogue_text = f"Error: initial script not found."

    def run_next_command(self):
        cmd, args = self.engine.get_next_command()
        if cmd is None: return 
            
        if cmd == "text": self.handle_text(args)
        elif cmd == "cleartext":
            if self.typewriter_event:
                self.typewriter_event.cancel()
                self.typewriter_event = None
            self.char_name = ""
            self.dialogue_text = ""
            self.run_next_command()
        elif cmd == "if":
            if not self.engine.evaluate_condition(args):
                while True:
                    next_cmd, _ = self.engine.get_next_command()
                    if next_cmd == "fi" or next_cmd is None: break
            self.run_next_command()
        elif cmd == "fi": self.run_next_command()
        elif cmd in ["bgload", "bg_load"]:
            clean_args = args.split()[0] if args else ""
            anim = Animation(transition_opacity=1.0, duration=0.3)
            anim.bind(on_complete=lambda *x: self._finish_bgload(clean_args))
            anim.start(self)
        elif cmd == "setimg": 
            self.handle_setimg(args)
        elif cmd == "clearimg":
            target = args.strip().lower()
            to_remove = []
            
            for char_id, info in self.active_sprites_info.items():
                if target == char_id or target == info['file'].lower() or target == info['pos']:
                    to_remove.append(char_id)
                    
            for char_id in to_remove:
                sprite = self.active_sprites.pop(char_id)
                self.active_sprites_info.pop(char_id)
                if 'sprite_layer' in self.ids:
                    anim = Animation(opacity=0.0, duration=0.3)
                    anim.bind(on_complete=lambda *x, s=sprite: self.ids.sprite_layer.remove_widget(s))
                    anim.start(sprite)
            self.run_next_command()
        elif cmd == "clearsprites":
            if 'sprite_layer' in self.ids: self.ids.sprite_layer.clear_widgets()
            self.active_sprites.clear()
            self.active_sprites_info.clear()
            self.run_next_command()
        elif cmd == "delay":
            try:
                p = int(args) / 1000.0 
                Clock.schedule_once(lambda dt: self.run_next_command(), p)
            except: self.run_next_command()
        elif cmd in ["setvar", "gsetvar"]:
            self.engine.handle_variable_assignment(args)
            self.run_next_command()
        elif cmd == "label": self.run_next_command()
        elif cmd == "goto":
            if args: self.engine.local_goto(args)
            self.run_next_command()
        elif cmd == "music":
            self.play_audio(args, True)
            self.run_next_command()
        elif cmd == "stopmusic":
            if self.current_music: self.current_music.stop()
            self.run_next_command()
        elif cmd == "sound":
            self.play_audio(args, False)
            self.run_next_command()
        elif cmd == "stopsound":
            if self.current_sound: self.current_sound.stop()
            self.run_next_command()
        elif cmd == "choice": 
            self.handle_choice(args)
            if self.auto_event: self.auto_event.cancel()
        elif cmd == "jump":
            jump_parts = args.split()
            if jump_parts:
                new_path = self.get_asset('script', jump_parts[0])
                if new_path:
                    self.engine.load_script(new_path)
                    if len(jump_parts) > 1: self.engine.local_goto(jump_parts[1])
            self.run_next_command()
        elif cmd == "hideui":
            self.hide_ui()
            self.run_next_command()
        elif cmd == "showui":
            self.unhide_ui()
            self.run_next_command()
        else: self.run_next_command()

    def _finish_bgload(self, clean_args):
        if 'sprite_layer' in self.ids: self.ids.sprite_layer.clear_widgets()
        self.active_sprites.clear()
        self.active_sprites_info.clear()
        
        self.current_bg_name = clean_args
        self.bg_source = self.get_asset('background', clean_args)
        
        anim = Animation(transition_opacity=0.0, duration=0.3)
        anim.bind(on_complete=lambda *x: self.run_next_command())
        anim.start(self)

    def handle_text(self, raw_text):
        text = raw_text.strip().strip('"').strip()
        
        if text in ["~", "!"]: self.char_name, self.full_text = "", ""
        elif text == "@":
            self.char_name = ""
            self.run_next_command()
            return
        elif text.startswith("@---"):
            end_idx = text.find("---", 4)
            if end_idx != -1:
                self.char_name = text[4:end_idx].strip()
                remaining = text[end_idx+3:].strip()
                if remaining: self.full_text = remaining
                else:
                    self.run_next_command()
                    return
            else: self.full_text = text
        elif text.startswith("@"): 
            space_idx = text.find(" ")
            if space_idx != -1:
                self.char_name = text[1:space_idx].strip()
                self.full_text = text[space_idx+1:].strip()
            else:
                self.char_name = text[1:].strip()
                self.run_next_command()
                return
        elif ":" in text and not text.startswith("http"):
            name, speech = text.split(":", 1)
            self.char_name, self.full_text = name.strip(), speech.strip()
        else: self.full_text = text

        self.char_name = self.char_name.strip().strip('"').strip()

        self.dialogue_text = ""
        self.type_index = 0
        if self.typewriter_event: self.typewriter_event.cancel()

        if self.full_text and text not in ["~", "!"]:
            formatted_name = f"[b][color=F2D966]{self.char_name}[/color][/b]\n" if self.char_name else ""
            
          
            self.dialogue_history.append({
                "scr": getattr(self.engine, 'current_script_name', ''),
                "text": formatted_name + self.full_text
            })
            
            self.typewriter_event = Clock.schedule_interval(self._type_next_char, 0.02)
        else:
            self.dialogue_text = self.full_text
            self.run_next_command()

    def _type_next_char(self, dt):
        if self.type_index < len(self.full_text):
            char = self.full_text[self.type_index]
            self.dialogue_text += char
            self.type_index += 1
            if char == '[':
                while self.type_index < len(self.full_text) and self.full_text[self.type_index-1] != ']':
                    self.dialogue_text += self.full_text[self.type_index]
                    self.type_index += 1
        else:
            if self.typewriter_event:
                self.typewriter_event.cancel()
                self.typewriter_event = None
            if self.auto_mode: self.trigger_auto()

    def handle_setimg(self, args):
        if 'sprite_layer' not in self.ids: 
            self.run_next_command()
            return
            
        p = args.split()
        if not p or p[0] == "~":
            self.ids.sprite_layer.clear_widgets()
            self.active_sprites.clear()
            self.active_sprites_info.clear()
            self.run_next_command()
            return
            
        filename = p[0]
        is_ui_element = filename.startswith("Date/") or filename.startswith("Location/")
        filepath = self.get_asset('foreground', filename)
        
        if not filepath or not os.path.exists(filepath):
            self.run_next_command()
            return

        if is_ui_element:
            img = KivyImage(source=filepath, allow_stretch=True, keep_ratio=True)
            img.size_hint = (None, None)
            img.bind(texture_size=img.setter('size'))
            if len(p) >= 3:
                try: img.pos = (float(p[1]), float(p[2]))
                except ValueError: pass
            img.opacity = 1
            self.ids.sprite_layer.add_widget(img)
            self.run_next_command()
            return

        char_id = filename.split('_')[0].split('.')[0].lower()

        if char_id in self.active_sprites:
            img = self.active_sprites[char_id]
            img.source = filepath
            self.active_sprites_info[char_id]['file'] = filename
            self.run_next_command()
            return

        img = KivyImage(source=filepath, allow_stretch=True, keep_ratio=True)
        img.size_hint = (None, 0.95)
        def scale_img(instance, *args_list):
            if instance.texture_size and instance.texture_size[1] > 0: 
                instance.width = instance.height * (instance.texture_size[0] / instance.texture_size[1])
        img.bind(height=scale_img, texture_size=scale_img)

        pos = "center"
        if len(p) >= 2:
            raw_pos = p[1].lower()
            if raw_pos in ["left", "l"]: pos = "left"
            elif raw_pos in ["right", "r"]: pos = "right"
            elif raw_pos in ["center", "c"]: pos = "center"

        anim_type = p[2].lower() if len(p) >= 3 else "fade"

        active_chars = list(self.active_sprites.keys())
        if len(active_chars) == 1:
            existing_char = active_chars[0]
            existing_pos = self.active_sprites_info[existing_char]['pos']
            
            if existing_pos == 'left': pos = 'right'
            elif existing_pos == 'right': pos = 'left'
            else:
                self.active_sprites_info[existing_char]['pos'] = 'left'
                existing_img = self.active_sprites[existing_char]
                existing_img.pos_hint = {'center_x': 0.25, 'y': 0.0}
                pos = 'right'

        if pos == 'left': img.pos_hint = {'center_x': 0.25, 'y': 0.0}
        elif pos == 'right': img.pos_hint = {'center_x': 0.75, 'y': 0.0}
        else: img.pos_hint = {'center_x': 0.5, 'y': 0.0}

        self.ids.sprite_layer.add_widget(img)
        self.active_sprites[char_id] = img
        self.active_sprites_info[char_id] = {'file': filename, 'pos': pos}

        if anim_type == "fade":
            img.opacity = 0
            Animation(opacity=1.0, duration=0.3).start(img)
        else:
            img.opacity = 1.0

        self.run_next_command()

    def restore_sprite(self, char_id, filename, pos_mode):
        filepath = self.get_asset('foreground', filename)
        if filepath and os.path.exists(filepath):
            img = KivyImage(source=filepath, allow_stretch=True, keep_ratio=True)
            img.size_hint = (None, 0.95)
            img.opacity = 1.0 
            
            def scale_img(instance, *args_list):
                if instance.texture_size and instance.texture_size[1] > 0: 
                    instance.width = instance.height * (instance.texture_size[0] / instance.texture_size[1])
            img.bind(height=scale_img, texture_size=scale_img)
            
            if pos_mode == 'left': img.pos_hint = {'center_x': 0.25, 'y': 0.0}
            elif pos_mode == 'right': img.pos_hint = {'center_x': 0.75, 'y': 0.0}
            else: img.pos_hint = {'center_x': 0.5, 'y': 0.0}
                    
            if 'sprite_layer' in self.ids: self.ids.sprite_layer.add_widget(img)
            self.active_sprites[char_id] = img
            self.active_sprites_info[char_id] = {'file': filename, 'pos': pos_mode}

    def handle_choice(self, args):
        self.auto_mode = False
        if args:
            self.choices = [choice.strip() for choice in args.split('|')]
        else:
            self.choices = []
            Logger.warning("Interpreter: Choice command triggered but no options were found.")
        self.is_choosing = True

    def select_choice(self, val):
        self.engine.variables["selected"] = val
        self.is_choosing = False
        self.run_next_command()

    def play_audio(self, raw_args, is_music=True):
        target = self.current_music if is_music else self.current_sound
        if target: target.stop()
        if raw_args == "~" or not raw_args: return
        parts = raw_args.split()
        filepath = self.get_asset('sound', parts[0])
        if filepath and os.path.exists(filepath):
            snd = SoundLoader.load(filepath)
            if snd:
                snd.volume = self.master_vol * (self.bgm_vol if is_music else self.sfx_vol)
                snd.loop = (is_music or (len(parts) > 1 and parts[1] == "-1"))
                snd.play()
                if is_music: self.current_music = snd
                else: self.current_sound = snd

    def toggle_drawer(self):
        if 'side_drawer' not in self.ids: return
        drawer = self.ids.side_drawer
        self.drawer_open = not self.drawer_open
        
        target_x = 0.65 if self.drawer_open else 1.0 
        
        anim = Animation(pos_hint={'x': target_x, 'y': 0.0}, duration=0.25, t='out_quad')
        anim.start(drawer)

    def close_drawer(self):
        if self.drawer_open:
            self.toggle_drawer()

    def next_line(self):
        if self.ui_hidden:
            self.unhide_ui()
            return
            
        if self.auto_event: self.auto_event.cancel() 
        
        if self.typewriter_event:
            self.typewriter_event.cancel()
            self.typewriter_event = None
            self.dialogue_text = self.full_text
            if self.auto_mode: self.trigger_auto()
        elif not self.is_choosing: 
            self.run_next_command()

    def trigger_auto(self):
        if self.auto_event: self.auto_event.cancel()
        if not self.is_choosing and self.dialogue_text:
            self.auto_event = Clock.schedule_once(lambda dt: self.next_line(), self.auto_speed)

    def toggle_auto(self):
        self.auto_mode = not self.auto_mode
        if self.auto_mode: 
            if not self.typewriter_event: self.trigger_auto()
        elif self.auto_event: self.auto_event.cancel()

    def hide_ui(self):
        self.ui_hidden = True
        self.ui_opacity = 0.0

    def unhide_ui(self):
        self.ui_hidden = False
        self.ui_opacity = 1.0

    def open_save_ui(self):
        SaveLoadPopup(self, mode='save').open()

    def open_load_ui(self):
        SaveLoadPopup(self, mode='load').open()

 
    def open_history(self):
        current_scr = getattr(self.engine, 'current_script_name', '')
        
        filtered_history = [item['text'] for item in self.dialogue_history if isinstance(item, dict) and item.get('scr') == current_scr]
        
        chunk_size = 15
        total_items = len(filtered_history)
        max_pages = max(1, (total_items + chunk_size - 1) // chunk_size)
        
        self._log_page = max_pages - 1
        
        content = BoxLayout(orientation='vertical', padding='10dp', spacing='10dp')
        
        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        grid = BoxLayout(orientation='vertical', size_hint_y=None, spacing='15dp', padding='5dp')
        grid.bind(minimum_height=grid.setter('height'))
        scroll.add_widget(grid)
        content.add_widget(scroll)

        nav_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height='50dp', spacing='10dp')
        
        prev_btn = Button(text="<", font_name='./assets/jpfont.ttf', font_size='26sp', background_normal='', background_color=(0,0,0,0), size_hint_x=0.2)
        next_btn = Button(text=">", font_name='./assets/jpfont.ttf', font_size='26sp', background_normal='', background_color=(0,0,0,0), size_hint_x=0.2)
        close_btn = Button(text="Close Log", font_name='./assets/jpfont.ttf', background_normal='', background_color=(0.2, 0.2, 0.22, 1), size_hint_x=0.6)
        
        nav_bar.add_widget(prev_btn)
        nav_bar.add_widget(close_btn)
        nav_bar.add_widget(next_btn)
        
        content.add_widget(nav_bar)

        popup = Popup(title="Message Log", title_font='./assets/jpfont.ttf', content=content, size_hint=(0.85, 0.85), background_color=(0.1, 0.1, 0.1, 0.95), separator_color=(0.4, 0.4, 0.4, 1))

        def render_page(*args):
            grid.clear_widgets()
            start_idx = self._log_page * chunk_size
            end_idx = start_idx + chunk_size
            
            page_data = filtered_history[start_idx:end_idx]
            for text in page_data:
                lbl = Label(text=text, markup=True, font_name='./assets/jpfont.ttf', font_size='16sp', size_hint_y=None, halign='left', valign='top', color=(0.95, 0.95, 0.95, 1))
                lbl.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
                lbl.bind(texture_size=lambda s, t: s.setter('height')(s, t[1]))
                grid.add_widget(lbl)

            prev_btn.opacity = 1.0 if self._log_page > 0 else 0.3
            next_btn.opacity = 1.0 if self._log_page < max_pages - 1 else 0.3

            Clock.schedule_once(lambda dt: setattr(scroll, 'scroll_y', 0.0), 0.1)

        def go_prev(*args):
            if self._log_page > 0:
                self._log_page -= 1
                render_page()

        def go_next(*args):
            if self._log_page < max_pages - 1:
                self._log_page += 1
                render_page()

        prev_btn.bind(on_release=go_prev)
        next_btn.bind(on_release=go_next)
        close_btn.bind(on_release=popup.dismiss)
        
        render_page()
        popup.open()

    def open_in_game_settings(self):
        disp_text = "Fixed" if self.bg_keep_ratio else "Full"
        
        kv_layout = f'''
BoxLayout:
    orientation: 'vertical'
    padding: '20dp'
    spacing: '15dp'
    
    ScrollView:
        do_scroll_x: False
        do_scroll_y: True
        
        BoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            spacing: '16dp'
            
            BoxLayout:
                size_hint_y: None
                height: '45dp'
                spacing: '10dp'
                Label:
                    text: "Auto Speed (s):"
                    font_name: './assets/jpfont.ttf'
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size
                    size_hint_x: 0.6
                
                AnchorLayout:
                    size_hint_x: 0.4
                    anchor_y: 'center'
                    TextInput:
                        id: speed_input
                        text: "{self.auto_speed}"
                        font_name: './assets/jpfont.ttf'
                        input_filter: 'float'
                        multiline: False
                        size_hint_y: None
                        height: '36dp'
                        background_normal: ''
                        background_color: 0.12, 0.12, 0.12, 1
                        foreground_color: 1, 1, 1, 1
                        halign: 'center'
                        padding: [0, (self.height - self.line_height) / 2, 0, 0]

            BoxLayout:
                size_hint_y: None
                height: '45dp'
                spacing: '10dp'
                Label:
                    text: "Display Mode:"
                    font_name: './assets/jpfont.ttf'
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size
                    size_hint_x: 0.6
                Button:
                    id: disp_btn
                    text: "{disp_text}"
                    font_name: './assets/jpfont.ttf'
                    background_normal: ''
                    background_color: 0, 0, 0, 0
                    size_hint_x: 0.4
                    on_release: self.text = "Full" if self.text == "Fixed" else "Fixed"
                    canvas.before:
                        Color:
                            rgba: (0.15, 0.15, 0.15, 1) if self.state == 'normal' else (0.25, 0.25, 0.25, 1)
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [dp(15)]

            BoxLayout:
                size_hint_y: None
                height: '45dp'
                spacing: '10dp'
                Label:
                    text: "Master Vol:"
                    font_name: './assets/jpfont.ttf'
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size
                    size_hint_x: 0.4
                Slider:
                    id: m_slider
                    min: 0.0
                    max: 1.0
                    value: {self.master_vol}
                    size_hint_x: 0.6
                    cursor_image: ''
                    cursor_size: (0, 0)
                    value_track: True
                    value_track_color: 1, 1, 1, 1
                    canvas.after:
                        Color:
                            rgba: 1, 1, 1, 1
                        Ellipse:
                            pos: self.value_pos[0] - dp(10), self.center_y - dp(10)
                            size: dp(20), dp(20)

            BoxLayout:
                size_hint_y: None
                height: '45dp'
                spacing: '10dp'
                Label:
                    text: "BGM Vol:"
                    font_name: './assets/jpfont.ttf'
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size
                    size_hint_x: 0.4
                Slider:
                    id: bgm_slider
                    min: 0.0
                    max: 1.0
                    value: {self.bgm_vol}
                    size_hint_x: 0.6
                    cursor_image: ''
                    cursor_size: (0, 0)
                    value_track: True
                    value_track_color: 1, 1, 1, 1
                    canvas.after:
                        Color:
                            rgba: 1, 1, 1, 1
                        Ellipse:
                            pos: self.value_pos[0] - dp(10), self.center_y - dp(10)
                            size: dp(20), dp(20)

            BoxLayout:
                size_hint_y: None
                height: '45dp'
                spacing: '10dp'
                Label:
                    text: "SFX Vol:"
                    font_name: './assets/jpfont.ttf'
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size
                    size_hint_x: 0.4
                Slider:
                    id: sfx_slider
                    min: 0.0
                    max: 1.0
                    value: {self.sfx_vol}
                    size_hint_x: 0.6
                    cursor_image: ''
                    cursor_size: (0, 0)
                    value_track: True
                    value_track_color: 1, 1, 1, 1
                    canvas.after:
                        Color:
                            rgba: 1, 1, 1, 1
                        Ellipse:
                            pos: self.value_pos[0] - dp(10), self.center_y - dp(10)
                            size: dp(20), dp(20)

    BoxLayout:
        orientation: 'horizontal'
        spacing: '15dp'
        size_hint_y: None
        height: '50dp'
        
        Button:
            id: close_btn
            text: "Cancel"
            font_name: './assets/jpfont.ttf'
            background_normal: ''
            background_color: 0, 0, 0, 0
            canvas.before:
                Color:
                    rgba: (0.25, 0.25, 0.28, 1) if self.state == 'normal' else (0.35, 0.35, 0.38, 1)
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(15)]
                    
        Button:
            id: apply_btn
            text: "Save Settings"
            font_name: './assets/jpfont.ttf'
            background_normal: ''
            background_color: 0, 0, 0, 0
            canvas.before:
                Color:
                    rgba: (0.2, 0.5, 0.2, 1) if self.state == 'normal' else (0.3, 0.6, 0.3, 1)
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(15)]
'''
        content = Builder.load_string(kv_layout)
        
        popup = Popup(
            title="In-Game Settings", 
            title_font='./assets/jpfont.ttf', 
            content=content, 
            size_hint=(0.7, 0.85),
            background_color=(0.08, 0.08, 0.08, 0.98), 
            separator_color=(0.3, 0.3, 0.3, 1)
        )
        
        content.ids.close_btn.bind(on_release=popup.dismiss)
        
        def apply_settings(instance):
            try: self.auto_speed = float(content.ids.speed_input.text)
            except ValueError: pass
            
            self.bg_keep_ratio = (content.ids.disp_btn.text == "Fixed")
            self.master_vol = content.ids.m_slider.value
            self.bgm_vol = content.ids.bgm_slider.value
            self.sfx_vol = content.ids.sfx_slider.value
            
            if self.current_music:
                self.current_music.volume = self.master_vol * self.bgm_vol
                
            config_file = './assets/saves/setting_configure.txt'
            try:
                os.makedirs(os.path.dirname(config_file), exist_ok=True)
                with open(config_file, 'w', encoding='utf-8') as f:
                    f.write(f"auto_speed={self.auto_speed}\n")
                    f.write(f"display_mode={content.ids.disp_btn.text}\n")
                    f.write(f"master_vol={self.master_vol}\n")
                    f.write(f"bgm_vol={self.bgm_vol}\n")
                    f.write(f"sfx_vol={self.sfx_vol}\n")
            except Exception as e:
                Logger.error(f"Settings file saving issue: {e}")
            popup.dismiss()
            
        content.ids.apply_btn.bind(on_release=apply_settings)
        popup.open()

    def exit_to_menu(self):
        content = BoxLayout(orientation='vertical', padding='15dp', spacing='15dp')
        msg = Label(text="Are you sure you want to return to the menu?\nUnsaved progress will be lost.", halign='center', valign='middle', font_size='16sp', font_name='./assets/jpfont.ttf')
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
        if self.typewriter_event: self.typewriter_event.cancel()
        if self.current_music: self.current_music.stop()
        if self.current_sound: self.current_sound.stop()
        App.get_running_app().root.current = 'menu_screen'

    def get_save_state(self):
        return {
            'game': self.current_game_folder,
            'script': getattr(self.engine, 'current_script_name', 'main.scr'),
            'line': self.engine.current_line_idx - 1, 
            'bg': self.current_bg_name, 
            'vars': self.engine.variables,
            'char_name': self.char_name,
            'full_text': self.full_text,
            'history': self.dialogue_history,
            'sprites': self.active_sprites_info.copy() 
        }

    def load_save_state(self, data):
        self.load_settings()  
        if self.auto_event: self.auto_event.cancel()
        if self.typewriter_event: self.typewriter_event.cancel()
        if self.current_music: self.current_music.stop()
        if self.current_sound: self.current_sound.stop()

        self.current_game_folder = data.get('game', '')
        self._apply_custom_ui()
        
        raw_history = data.get('history', [])
        self.dialogue_history = []
        for item in raw_history:
            if isinstance(item, str):
                self.dialogue_history.append({"scr": data.get('script', ''), "text": item})
            else:
                self.dialogue_history.append(item)

        self.engine.variables = data.get('vars', {})
        self.char_name = data.get('char_name', '')
        self.full_text = data.get('full_text', '')
        
        self.dialogue_text = self.full_text 
        
        self.current_bg_name = data.get('bg', '')
        if self.current_bg_name: self.bg_source = self.get_asset('background', self.current_bg_name)
        else: self.bg_source = ""
       
        if 'sprite_layer' in self.ids: self.ids.sprite_layer.clear_widgets()
        self.active_sprites.clear()
        self.active_sprites_info.clear()
        
        saved_sprites = data.get('sprites', {})

        for char_id, info in saved_sprites.items():
            self.restore_sprite(char_id, info['file'], info['pos'])

        script_name = data.get('script', 'main.scr')
        target_script = self.get_asset('script', script_name)
        
        if target_script and os.path.exists(target_script):
            self.engine.load_script(target_script)
            self.engine.current_line_idx = max(0, data.get('line', 0))
        else:
            Logger.error(f"Interpreter: Missing Script {script_name}")
            return
            
        for i in range(self.engine.current_line_idx - 1, -1, -1):
            if i < len(self.engine.script_lines):
                line = self.engine.script_lines[i].strip()
                parts = line.split(' ', 1)
                cmd = parts[0].lower()
                if cmd == "music":
                    args = parts[1] if len(parts) > 1 else ""
                    self.play_audio(args, True)
                    break
        
        self.run_next_command()
