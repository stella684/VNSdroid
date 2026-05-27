import os
from kivy.config import Config
Config.set('graphics', 'resizable', '1')

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivy.utils import platform

if platform != 'android':
    Window.size = (1280, 720)

from modules.menu_logic import MainMenu
from modules.game_interpreter import VNInterpreter
from modules.settings_logic import SettingsMenu
from modules.github import GithubMenu

Builder.load_file('./assets/kv/menu.kv')
Builder.load_file('./assets/kv/game.kv')
Builder.load_file('./assets/kv/saveload.kv')
Builder.load_file('./assets/kv/settings.kv')
Builder.load_file('./assets/kv/github.kv')

def set_android_orientation(orientation='portrait'):
    if platform == 'android':
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Activity = PythonActivity.mActivity
            ActivityInfo = autoclass('android.content.pm.ActivityInfo')
            if orientation == 'landscape':
                Activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE)
            else:
                Activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT)
        except Exception as e:
            pass

class MainMenuScreen(Screen):
    def on_pre_enter(self, *args):
        set_android_orientation('portrait')

    def on_kv_post(self, base_widget):
        self.menu_widget = MainMenu()
        self.add_widget(self.menu_widget)

class GameScreen(Screen):
    def on_pre_enter(self, *args):
        set_android_orientation('landscape')

    def on_kv_post(self, base_widget):
        self.interpreter_widget = VNInterpreter()
        self.add_widget(self.interpreter_widget)

class SettingsScreen(Screen):
    def on_pre_enter(self, *args):
        set_android_orientation('portrait')

    def on_kv_post(self, base_widget):
        self.settings_widget = SettingsMenu()
        self.add_widget(self.settings_widget)

class GithubScreen(Screen):
    def on_pre_enter(self, *args):
        set_android_orientation('portrait')

    def on_kv_post(self, base_widget):
        self.github_widget = GithubMenu()
        self.add_widget(self.github_widget)

class VNSdroidApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MainMenuScreen(name='menu_screen'))
        sm.add_widget(GameScreen(name='game_screen'))
        sm.add_widget(SettingsScreen(name='settings_screen'))
        sm.add_widget(GithubScreen(name='github_screen'))
        return sm

if __name__ == '__main__':
    VNSdroidApp().run()
