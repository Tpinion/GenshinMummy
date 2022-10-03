import time

import pyautogui

from .locator import is_menu_page, locate

LITTLE_MOVE = 5

MOUSE_MOVE_TIME = 0.2
KEY_PRESS_PAUSE = 0.1
CLICK_INTERVAL = 3

RENDERING_TIME = 0.5


def wait_rendering():
    time.sleep(RENDERING_TIME)


def select_menu_page():
    pyautogui.press("esc", interval=RENDERING_TIME)
    while not is_menu_page():
        pyautogui.press("esc", interval=RENDERING_TIME)


def select_main_page():
    select_menu_page()
    pyautogui.press('esc', interval=RENDERING_TIME)


def select_inventory_page():
    select_menu_page()
    key = 'inventory_icon'
    inventory_icon_pos = locate(key)
    pyautogui.leftClick(*inventory_icon_pos, duration=MOUSE_MOVE_TIME)


def select_artifact_on_inventory_page():
    key = 'artifact_icon'
    wait_rendering()
    artifact_icon_pos = locate(key, True)
    if artifact_icon_pos is None:
        locate(key, extension_mode=True)
    pyautogui.leftClick(*artifact_icon_pos, duration=MOUSE_MOVE_TIME)


def select_weapon_on_inventory_page():
    key = 'weapon_icon'
    wait_rendering()
    artifact_icon_pos = locate(key)
    if artifact_icon_pos is None:
        locate(key, extension_mode=True)
    pyautogui.leftClick(*artifact_icon_pos, duration=MOUSE_MOVE_TIME)


def select_artifact_page():
    select_inventory_page()
    # TODO: init and cache those fixed icons' position.
    select_artifact_on_inventory_page()


if __name__ == '__main__':
    time.sleep(2)
    select_artifact_page()
