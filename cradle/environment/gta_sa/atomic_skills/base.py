import platform
import time

import pyautogui

try:
    import pydirectinput
except Exception:
    pydirectinput = None

from cradle.config import Config
from cradle.log import Logger
from cradle.environment import post_skill_wait
from cradle.environment.gta_sa.skill_registry import register_skill


config = Config()
logger = Logger()

if pydirectinput is not None:
    pydirectinput.FAILSAFE = False


def _ensure_game_active():
    env_window = getattr(config, "env_window", None)
    if env_window is not None:
        try:
            env_window.activate()
            time.sleep(0.2)
        except Exception:
            pass


def _normalize_key_name(key):
    aliases = {
        "return": "enter",
        "esc": "escape",
    }

    if isinstance(key, str):
        return aliases.get(key.lower(), key)

    return key


def _press_key(key):
    _ensure_game_active()
    key = _normalize_key_name(key)
    if platform.system() == "Windows" and pydirectinput is not None:
        pydirectinput.press(key)
    else:
        pyautogui.press(key)


def _key_down(key):
    _ensure_game_active()
    key = _normalize_key_name(key)
    if platform.system() == "Windows" and pydirectinput is not None:
        pydirectinput.keyDown(key)
    else:
        pyautogui.keyDown(key)


def _key_up(key):
    _ensure_game_active()
    key = _normalize_key_name(key)
    if platform.system() == "Windows" and pydirectinput is not None:
        pydirectinput.keyUp(key)
    else:
        pyautogui.keyUp(key)


def _move_to_absolute(x, y):
    _ensure_game_active()
    screen_width, screen_height = pyautogui.size()
    env_region = getattr(config, "env_region", (0, 0, screen_width, screen_height))
    abs_x = int(env_region[0] + (x * env_region[2]))
    abs_y = int(env_region[1] + (y * env_region[3]))
    pyautogui.moveTo(abs_x, abs_y)


@register_skill("move_mouse_to_position")
def move_mouse_to_position(x, y):
    """
    Move the mouse to a normalized x, y position.

    Parameters:
    - x: The normalized x-coordinate of the target position. The value should be between 0 and 1.
    - y: The normalized y-coordinate of the target position. The value should be between 0 and 1.
    """
    _move_to_absolute(x, y)
    post_skill_wait(config.DEFAULT_POST_ACTION_WAIT_TIME)


@register_skill("click_at_position")
def click_at_position(x, y, mouse_button):
    """
    Move the mouse to a normalized x, y position and click.

    Parameters:
    - x: The normalized x-coordinate of the target position. The value should be between 0 and 1.
    - y: The normalized y-coordinate of the target position. The value should be between 0 and 1.
    - mouse_button: The mouse button to be clicked. It should be one of the following values: "left", "right", "middle".
    """
    _move_to_absolute(x, y)
    pyautogui.click(button=mouse_button)
    post_skill_wait(config.DEFAULT_POST_ACTION_WAIT_TIME)


@register_skill("double_click_at_position")
def double_click_at_position(x, y, mouse_button):
    """
    Move the mouse to a normalized x, y position and double click.

    Parameters:
    - x: The normalized x-coordinate of the target position. The value should be between 0 and 1.
    - y: The normalized y-coordinate of the target position. The value should be between 0 and 1.
    - mouse_button: The mouse button to be clicked. It should be one of the following values: "left", "right", "middle".
    """
    _move_to_absolute(x, y)
    pyautogui.click(button=mouse_button)
    pyautogui.click(button=mouse_button)
    post_skill_wait(config.DEFAULT_POST_ACTION_WAIT_TIME)


@register_skill("mouse_drag")
def mouse_drag(source_x, source_y, target_x, target_y, mouse_button):
    """
    Drag the mouse from a source position to a target position.

    Parameters:
    - source_x: The normalized x-coordinate of the source position. The value should be between 0 and 1.
    - source_y: The normalized y-coordinate of the source position. The value should be between 0 and 1.
    - target_x: The normalized x-coordinate of the target position. The value should be between 0 and 1.
    - target_y: The normalized y-coordinate of the target position. The value should be between 0 and 1.
    - mouse_button: The mouse button to be held during drag. It should be one of the following values: "left", "right", "middle".
    """
    _move_to_absolute(source_x, source_y)
    pyautogui.mouseDown(button=mouse_button)
    _move_to_absolute(target_x, target_y)
    pyautogui.mouseUp(button=mouse_button)
    post_skill_wait(config.DEFAULT_POST_ACTION_WAIT_TIME)


@register_skill("mouse_scroll_down")
def mouse_scroll_down(distance):
    """
    Scroll down with the mouse wheel.

    Parameters:
    - distance: Number of wheel steps to scroll down.
    """
    pyautogui.scroll(-abs(distance))


@register_skill("mouse_scroll_up")
def mouse_scroll_up(distance):
    """
    Scroll up with the mouse wheel.

    Parameters:
    - distance: Number of wheel steps to scroll up.
    """
    pyautogui.scroll(abs(distance))


@register_skill("press_key")
def press_key(key):
    """
    Press a keyboard key.

    Parameters:
    - key: A keyboard key to be pressed. For example, press the 'enter' key.
    """
    _press_key(key)


@register_skill("hold_key")
def hold_key(key):
    """
    Hold a keyboard key down until a release call happens.

    Parameters:
    - key: A keyboard key to be held. For example, hold the 'shift' key.
    """
    _key_down(key)


@register_skill("release_key")
def release_key(key):
    """
    Release a keyboard key.

    Parameters:
    - key: A keyboard key to be released. For example, release the 'shift' key.
    """
    _key_up(key)


@register_skill("press_keys_combined")
def press_keys_combined(keys):
    """
    Press keys together.

    Parameters:
    - keys: List of keys to press together at the same time. Either list of key names, or a string of comma-separated key names.
    """
    if isinstance(keys, str):
        keys = [key.strip() for key in keys.split(",") if key.strip()]

    if platform.system() == "Windows" and pydirectinput is not None:
        pydirectinput.hotkey(*keys)
    else:
        pyautogui.hotkey(*keys)


@register_skill("type_text")
def type_text(text):
    """
    Type text with the keyboard.

    Parameters:
    - text: The text to be typed into the current UI control.
    """
    pyautogui.write(text, interval=0.02)
    post_skill_wait(config.DEFAULT_POST_ACTION_WAIT_TIME)


@register_skill("move_forward")
def move_forward(duration=0.5):
    """
    Move the player forward.

    Parameters:
    - duration: Duration in seconds to hold the forward key.
    """
    _key_down("w")
    time.sleep(duration)
    _key_up("w")


@register_skill("move_backward")
def move_backward(duration=0.5):
    """
    Move the player backward.

    Parameters:
    - duration: Duration in seconds to hold the backward key.
    """
    _key_down("s")
    time.sleep(duration)
    _key_up("s")


@register_skill("move_left")
def move_left(duration=0.5):
    """
    Strafe left.

    Parameters:
    - duration: Duration in seconds to hold the left key.
    """
    _key_down("a")
    time.sleep(duration)
    _key_up("a")


@register_skill("move_right")
def move_right(duration=0.5):
    """
    Strafe right.

    Parameters:
    - duration: Duration in seconds to hold the right key.
    """
    _key_down("d")
    time.sleep(duration)
    _key_up("d")


@register_skill("turn_left")
def turn_left(duration=0.5):
    """
    Turn the camera left.

    Parameters:
    - duration: Duration in seconds to hold the turn key.
    """
    _key_down("a")
    time.sleep(duration)
    _key_up("a")


@register_skill("turn_right")
def turn_right(duration=0.5):
    """
    Turn the camera right.

    Parameters:
    - duration: Duration in seconds to hold the turn key.
    """
    _key_down("d")
    time.sleep(duration)
    _key_up("d")


@register_skill("run_forward")
def run_forward(duration=0.5):
    """
    Run forward.

    Parameters:
    - duration: Duration in seconds to hold the run keys.
    """
    _key_down("shift")
    _key_down("w")
    time.sleep(duration)
    _key_up("w")
    _key_up("shift")


@register_skill("jump")
def jump():
    """
    Jump once.
    """
    _press_key("space")


@register_skill("enter_vehicle")
def enter_vehicle():
    """
    Enter or exit a nearby vehicle.
    """
    _press_key("f")


@register_skill("attack")
def attack():
    """
    Attack or fire the current weapon.
    """
    pyautogui.click(button="left")
