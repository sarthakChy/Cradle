import time

import pyautogui
import pygetwindow as gw
from PIL import Image
import mss

from cradle.config import Config
from cradle.log import Logger
from cradle.environment import UIControl
from cradle import constants


config = Config()
logger = Logger()


class GtaSaUIControl(UIControl):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _find_window(self):
        windows = gw.getWindowsWithTitle(config.env_name)
        if (windows is None or len(windows) == 0) and len(getattr(config, "win_name_pattern", "")) > 0:
            windows = gw.getWindowsWithTitle(config.win_name_pattern)
        return windows[0] if windows else None

    def pause_game(self, env_name: str, ide_name: str) -> None:
        return

    def unpause_game(self, env_name: str, ide_name: str) -> None:
        return

    def switch_to_game(self, env_name: str, ide_name: str) -> None:
        window = self._find_window()
        if window is None:
            raise EnvironmentError(f"Cannot find the GTA SA window: {config.env_name} | {config.win_name_pattern}")

        try:
            window.activate()
        except Exception:
            try:
                window.restore()
                window.activate()
            except Exception:
                pass

        config.env_window = window
        time.sleep(1)

    def exit_back_to_pause(self, env_name: str, ide_name: str) -> None:
        pyautogui.press("esc")
        time.sleep(constants.PAUSE_SCREEN_WAIT)

    def exit_back_to_game(self, env_name: str, ide_name: str) -> None:
        self.exit_back_to_pause(env_name, ide_name)
        self.unpause_game(env_name, ide_name)

    def is_env_paused(self) -> bool:
        return False

    def take_screenshot(self, tid: float, screen_region: tuple[int, int, int, int] = None) -> str:
        if screen_region is None:
            screen_region = getattr(config, "env_region", None)

        if screen_region is None:
            screen_region = (0, 0, pyautogui.size().width, pyautogui.size().height)

        region = {
            "left": screen_region[0],
            "top": screen_region[1],
            "width": screen_region[2],
            "height": screen_region[3],
        }

        output_dir = config.work_dir
        screen_image_filename = output_dir + "/screen_" + str(tid) + ".jpg"

        with mss.mss() as sct:
            screen_image = sct.grab(region)
            image = Image.frombytes("RGB", screen_image.size, screen_image.bgra, "raw", "BGRX")
            image.save(screen_image_filename)

        return screen_image_filename
