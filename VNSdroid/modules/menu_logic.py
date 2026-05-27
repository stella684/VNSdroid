import os
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.properties import StringProperty
from kivy.app import App
from kivy.logger import Logger
from kivy.lang import Builder
from kivy.factory import Factory

Builder.load_string('''
<MenuDialogButton@Button>:
    font_name: './assets/jpfont.ttf'
    background_normal: ''
    background_color: 0, 0, 0, 0
    color: 0.95, 0.95, 0.95, 1
    canvas.before:
        Color:
            rgba: (0.22, 0.22, 0.25, 1) if self.state == 'normal' else (0.3, 0.3, 0.35, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(15)]
''')

class GameItem(ButtonBehavior, BoxLayout):
    game_name = StringProperty("")
    icon_path = StringProperty("")
    game_folder_path = StringProperty("")

class MainMenu(BoxLayout):
    app_version = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.load_version()
        self.load_games()

    def load_version(self):
        version_file = './version.txt'
        if os.path.exists(version_file):
            try:
                with open(version_file, 'r', encoding='utf-8') as f:
                    self.app_version = f.read().strip()
            except Exception as e:
                Logger.error(f"MenuLogic: Failed to read {version_file}. Error: {e}")
        else:
            self.app_version = "v?.?"

    def load_games(self):
        games_dir = './games'
        if not os.path.exists(games_dir):
            os.makedirs(games_dir)
            return

        for folder in sorted(os.listdir(games_dir)):
            folder_path = os.path.join(games_dir, folder)
            if not os.path.isdir(folder_path):
                continue

            target_path = folder_path

            if not os.path.exists(os.path.join(target_path, 'info.txt')):
                for sub in os.listdir(target_path):
                    sub_path = os.path.join(target_path, sub)
                    if os.path.isdir(sub_path) and os.path.exists(os.path.join(sub_path, 'info.txt')):
                        target_path = sub_path
                        break

            info_path = os.path.join(target_path, 'info.txt')
            icon_path = os.path.join(target_path, 'icon.png')

            game_name = self.parse_game_name(info_path, default=folder)
            final_icon = icon_path if os.path.exists(icon_path) else "atlas://data/images/defaulttheme/bubble"

            item_widget = GameItem(
                game_name=game_name,
                icon_path=final_icon,
                game_folder_path=target_path
            )
            
            item_widget.bind(
                on_release=lambda btn, n=game_name, p=target_path: self.show_confirm_popup(n, p)
            )
            self.ids.games_list.add_widget(item_widget)

    def parse_game_name(self, info_path, default):
        if os.path.exists(info_path):
            try:
                with open(info_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('name='):
                            return line.split('=', 1)[1].strip()
            except Exception as e:
                Logger.error(f"MenuLogic: Failed to parse {info_path}. {e}")
        return default

    def show_confirm_popup(self, game_title, game_folder_path):
        content = BoxLayout(orientation='vertical', padding='15dp', spacing='15dp')

        msg = Label(
            text=f"Do you really want to start\n[b]{game_title}[/b]?",
            markup=True,
            halign='center',
            valign='middle',
            font_size='16sp',
            color=(0.95, 0.95, 0.95, 1),
            font_name='./assets/jpfont.ttf'
        )
        msg.bind(size=msg.setter('text_size'))
        content.add_widget(msg)

        btn_layout = BoxLayout(orientation='horizontal', spacing='10dp', size_hint_y=None, height='45dp')
        cancel_btn = Factory.MenuDialogButton(text="Cancel")
        confirm_btn = Factory.MenuDialogButton(text="Start Game")
        btn_layout.add_widget(cancel_btn)
        btn_layout.add_widget(confirm_btn)
        content.add_widget(btn_layout)

        popup = Popup(
            title="Launch Game",
            title_font='./assets/jpfont.ttf',
            content=content,
            size_hint=(None, None),
            size=('320dp', '180dp'),
            auto_dismiss=True,
            background_color=(0.11, 0.11, 0.13, 0.95),
            title_align='center',
            title_color=(0.9, 0.9, 0.9, 1),
            separator_color=(0.3, 0.3, 0.35, 1)
        )

        cancel_btn.bind(on_release=popup.dismiss)
        confirm_btn.bind(on_release=lambda btn, p=game_folder_path: self.confirm_and_launch(p, popup))
        popup.open()

    def confirm_and_launch(self, game_folder_path, popup):
        popup.dismiss()
        app = App.get_running_app()
        game_screen = app.root.get_screen('game_screen')
        interpreter = game_screen.interpreter_widget

        if 'sprite_layer' in interpreter.ids:
            interpreter.ids.sprite_layer.clear_widgets()

        interpreter.start_story(game_folder_path)
        app.root.current = 'game_screen'
