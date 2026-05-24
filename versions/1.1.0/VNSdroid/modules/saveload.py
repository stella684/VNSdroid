import os
import json
from datetime import datetime
from kivy.uix.modalview import ModalView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.logger import Logger
from kivy.properties import StringProperty
from kivy.app import App
from kivy.factory import Factory

class SaveLoadPopup(ModalView):
    mode = StringProperty('save')

    def __init__(self, interpreter=None, mode='save', **kwargs):
        super().__init__(mode=mode, **kwargs)
        self.interpreter = interpreter
        
        game_folder_name = "default"
        if self.interpreter and self.interpreter.current_game_folder:
            game_folder_name = os.path.basename(os.path.normpath(self.interpreter.current_game_folder))

        self.save_dir = os.path.join('./saves', game_folder_name)
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

    def on_open(self):
        self.populate_slots()

    def populate_slots(self):
        if 'slot_container' not in self.ids:
            return
            
        container = self.ids.slot_container
        container.clear_widgets()
        
        for i in range(1, 21):
            filepath = os.path.join(self.save_dir, f'slot_{i}.json')
            
            slot_name = ""
            btn_text = ""
            bg_file_name = ""
            
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        save_data = json.load(f)
                    slot_name = save_data.get('slot_name', '')
                    bg_file_name = save_data.get('bg', '')
                except Exception:
                    slot_name = ''
                    
                mtime = os.path.getmtime(filepath)
                timestamp = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d  %H:%M')

                if slot_name:
                    btn_text = f"Slot {i}: {slot_name}\n[size=14sp][color=AAAAAA]{timestamp}[/color][/size]"
                else:
                    btn_text = f"Slot {i}\n[size=14sp][color=AAAAAA]{timestamp}[/color][/size]"
            else:
                btn_text = f"Slot {i}\n[size=14sp][color=555555]--- Empty ---[/color][/size]"
                
            # Live resolve asset path instead of loading written png thumbnails from file storage
            thumb_src = './assets/icon.png'
            if bg_file_name and self.interpreter:
                resolved_bg = self.interpreter.get_asset('background', bg_file_name)
                if resolved_bg and os.path.exists(resolved_bg):
                    thumb_src = resolved_bg

            item = Factory.SlotItem()
            item.slot_num = i
            item.popup_ref = self
            item.thumb_source = thumb_src
            item.slot_text = btn_text
            
            item.bind(on_release=lambda instance, s=i: self.select_slot(s))
            container.add_widget(item)

    def select_slot(self, slot_num):
        filepath = os.path.join(self.save_dir, f'slot_{slot_num}.json')
        app = App.get_running_app()
        
        if not self.interpreter:
            self.interpreter = app.root.get_screen('game_screen').interpreter_widget

        if self.mode == 'save':
            self.prompt_save_name(slot_num, filepath)
        else: 
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    self.interpreter.load_save_state(data)
                    Logger.info(f"SaveLoad: Slot {slot_num} loaded successfully.")
                    app.root.current = 'game_screen'
                except Exception as e:
                    Logger.error(f"Load Error: {e}")
            else:
                Logger.info(f"Load: Slot {slot_num} is empty.")
                return 
                
            self.dismiss()

    def prompt_save_name(self, slot_num, filepath):
        content = BoxLayout(orientation='vertical', spacing='10dp', padding='10dp')
        
        name_input = TextInput(
            hint_text="Enter custom save name (optional)...", 
            multiline=False, 
            size_hint_y=None, 
            height='45dp',
            background_color=(0.1, 0.1, 0.1, 1),
            foreground_color=(1, 1, 1, 1),
            font_name='./assets/jpfont.ttf'
        )
        
        btn_layout = BoxLayout(orientation='horizontal', spacing='10dp', size_hint_y=None, height='45dp')
        cancel_btn = Button(text="Cancel", font_name='./assets/jpfont.ttf', background_normal='', background_color=(0.2, 0.2, 0.2, 1))
        save_btn = Button(text="Save", font_name='./assets/jpfont.ttf', background_normal='', background_color=(0.2, 0.6, 0.2, 1))
        
        btn_layout.add_widget(cancel_btn)
        btn_layout.add_widget(save_btn)
        
        content.add_widget(name_input)
        content.add_widget(btn_layout)
        
        name_popup = Popup(
            title=f"Name for Slot {slot_num}",
            title_font='./assets/jpfont.ttf',
            content=content,
            size_hint=(None, None),
            size=('320dp', '160dp'),
            auto_dismiss=True,
            background_color=(0.1, 0.1, 0.1, 0.95),
            separator_color=(0.4, 0.4, 0.4, 1)
        )
        
        def execute_save(instance):
            name_popup.dismiss()
            if self.interpreter:
                data = self.interpreter.get_save_state()
                data['slot_name'] = name_input.text.strip()
                try:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4)

                    Logger.info(f"SaveLoad: Progress saved to slot {slot_num}.")
                    self.populate_slots() 
                except Exception as e:
                    Logger.error(f"Save Error: {e}")
                    
        cancel_btn.bind(on_release=name_popup.dismiss)
        save_btn.bind(on_release=execute_save)
        name_popup.open()
