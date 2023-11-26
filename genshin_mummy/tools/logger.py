from threading import Thread
from tkinter import (
    END,
    HORIZONTAL,
    VERTICAL,
    Canvas,
    Listbox,
    Scrollbar,
    Tk,
    Label,
)
from typing import Optional, Tuple, Union
from enum import Enum

import attrs

from genshin_mummy.type import Box

TRANSPARENT_COLOR = 'black'
FONT_COLOR = '#2F7AFF'


class WidgetPosition(Enum):
    CENTER = 'center'
    TOP_LEFT = 'top_left'
    BOTTOM_CENTER = 'bottom_center'


@attrs.define
class Logger:
    widget: Optional[Tk] = attrs.field(default=None)
    listbox: Optional[Listbox] = attrs.field(default=None)

    def __attrs_post_init__(self):
        Thread(
            target=self.init_screen_logger,
            daemon=True,
        ).start()

    def init_screen_logger(self):
        widget = self.create_widget(
            size=(0.5, 0.05),
            position=WidgetPosition.BOTTOM_CENTER,
            alpha=0.5,
        )
        self.widget = widget

        vert_bar = Scrollbar(widget, orient=VERTICAL)
        # hori_bar = Scrollbar(widget, orient=HORIZONTAL)
        self.listbox = Listbox(
            widget,
            # xscrollcommand=hori_bar.set,
            yscrollcommand=vert_bar.set,
            borderwidth=0,
            width=widget.winfo_width(),
        )
        # hori_bar.config(command=self.listbox.xview)
        vert_bar.config(command=self.listbox.yview)

        # hori_bar.pack(side="bottom", fill="x")
        vert_bar.pack(side="right", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True)

        widget.mainloop()

    def hidden_logger(self):
        if self.widget:
            self.widget.withdraw()

    def show_logger(self):
        if self.widget:
            self.widget.deiconify()

    def info(self, message: str):
        message = f'INFO: {message}'
        if self.listbox:
            self.listbox.insert(END, message)
            self.listbox.see(END)

    def warning(self, message: str):
        message = f'WARNING: {message}'
        if self.listbox:
            self.listbox.insert(END, message)
            self.listbox.see(END)

    def create_widget(
        self,
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

        widget_width = int(size[0] * screen_width) if isinstance(
            size[0], float) else size[0]
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
        widget = self.create_widget(position=WidgetPosition.CENTER)
        label = self.default_label(widget, message)
        label.place(relwidth=1, rely=0.5)
        widget.after(destory_ms, widget.destroy)
        widget.mainloop()

    def notify_countdown(self, seconds: int):
        widget = self.create_widget(position=WidgetPosition.CENTER)
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
        widget = self.create_widget()

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


if __name__ == '__main__':
    import time
    logger = Logger()
    logger.show_bbox(Box(0, 0, 100, 100))
