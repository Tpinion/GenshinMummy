import logging
import time
from enum import Enum
from logging import FileHandler, Handler
from os import PathLike
from threading import Thread
from tkinter import (
    END,
    VERTICAL,
    Canvas,
    Label,
    Listbox,
    Scrollbar,
    Tk,
)
from typing import Tuple, Union

from genshin_mummy.type import Box

TRANSPARENT_COLOR = 'black'
FONT_COLOR = '#2F7AFF'


class WidgetPosition(Enum):
    CENTER = 'center'
    TOP_LEFT = 'top_left'
    BOTTOM_CENTER = 'bottom_center'


def create_widget(
    size: Tuple[Union[int, float], Union[int, float]] = (1.0, 1.0),
    position: WidgetPosition = WidgetPosition.TOP_LEFT,
    alpha: float = 1.0,
    bg: str = TRANSPARENT_COLOR,
):
    widget = Tk()
    widget.configure(bg=bg)
    widget.overrideredirect(True)
    widget.attributes('-topmost', True)
    widget.attributes('-alpha', alpha)

    widget.wm_attributes('-transparentcolor', TRANSPARENT_COLOR)

    screen_width = widget.winfo_screenwidth()
    screen_height = widget.winfo_screenheight()

    widget_width = int(size[0] *
                       screen_width) if isinstance(size[0], float) else size[0]
    widget_height = int(size[1] * screen_height) if isinstance(
        size[1], float) else size[1]

    if position == WidgetPosition.TOP_LEFT:
        x = 0
        y = 0
    elif position == WidgetPosition.CENTER:
        x = (screen_width - widget_width) // 2
        y = (screen_height - widget_height) // 2
    elif position == WidgetPosition.BOTTOM_CENTER:
        x = (screen_width - widget_width) // 2
        y = screen_height - widget_height
    else:
        raise NotImplementedError()

    widget.geometry(f'{widget_width}x{widget_height}+{x}+{y}')

    return widget


class ScreenHandler(Handler):

    def __init__(self):
        super().__init__()
        self.widget = None
        self.listbox = None

        Thread(
            target=self.init_screen_logger,
            daemon=True,
        ).start()
        time.sleep(1)

    def init_screen_logger(self):
        widget = create_widget(
            size=(0.5, 0.05),
            position=WidgetPosition.BOTTOM_CENTER,
            alpha=0.5,
        )
        self.widget = widget

        vert_bar = Scrollbar(widget, orient=VERTICAL)
        self.listbox = Listbox(
            widget,
            yscrollcommand=vert_bar.set,
            borderwidth=0,
            width=widget.winfo_width(),
        )
        vert_bar.config(command=self.listbox.yview)

        vert_bar.pack(side="right", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True)

        widget.mainloop()

    def emit(self, record):
        self.listbox.insert(END, self.format(record))
        self.listbox.see(END)


class ExLogger(logging.Logger):

    def __init__(self, name: str, level: int = logging.NOTSET):
        super().__init__(name, level)

    def default_label(self, widget: Tk, message: str):
        screen_width = widget.winfo_screenwidth()
        label = Label(
            widget,
            text=message,
            bg=TRANSPARENT_COLOR,
            fg=FONT_COLOR,
            font=(None, 50, 'bold'),
            anchor='center',
            wraplength=screen_width // 2,
        )
        return label

    def notify(self, message: str, destory_ms: int = 2000):
        widget = create_widget(position=WidgetPosition.CENTER)
        label = self.default_label(widget, message)
        label.place(relwidth=1, rely=0.5)
        widget.after(destory_ms, widget.destroy)
        widget.mainloop()

    def notify_countdown(self, seconds: int):
        widget = create_widget(position=WidgetPosition.CENTER)
        label = self.default_label(widget, '倒计时即将开始')
        label.place(relwidth=1, rely=0.5)

        def countdown(widget, label, seconds):
            if seconds == 0:
                widget.destroy()
            else:
                label['text'] = seconds
                widget.after(1000, countdown, widget, label, seconds - 1)

        widget.after(1000, countdown, widget, label, seconds)
        widget.mainloop()

    def show_bbox(self, box: Box, box_name: str = ''):
        widget = create_widget()

        canvas = Canvas(
            widget,
            width=widget.winfo_screenwidth(),
            height=widget.winfo_screenheight(),
            bg=TRANSPARENT_COLOR,
            highlightthickness=0,
        )
        canvas.pack()

        label = Label(
            widget,
            text=box_name,
            bg=TRANSPARENT_COLOR,
            fg=FONT_COLOR,
            font=(None, 20, 'bold'),
        )
        label.place(x=box.left, y=box.top)
        label.lift()

        canvas.create_rectangle(
            box.left,
            box.top,
            box.right,
            box.bottom,
            outline=FONT_COLOR,
            width=4,
        )

        widget.after(3000, widget.destroy)
        widget.mainloop()


def create_logger(name: str, logger_folder: PathLike) -> ExLogger:
    logger = logging.getLogger(name)
    logger.__class__ = ExLogger
    logger.setLevel(logging.INFO)
    file_handler = FileHandler(logger_folder / 'mummy.log')
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger
