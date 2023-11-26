from tkinter import Tk, Label

TRANSPARENT_COLOR = 'black'


def move_window_to_screen_center(window: Tk):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    window_width = window.winfo_width()
    window_height = window.winfo_height()

    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2

    window.geometry(f'+{x}+{y}')


def create_notification_window():

    notification_window = Tk()
    notification_window.attributes('-topmost', True)

    notification_window.overrideredirect(True)
    notification_window.wm_attributes('-transparentcolor', TRANSPARENT_COLOR)
    return notification_window


def default_label(message: str):
    return Label(
        text=message,
        bg=TRANSPARENT_COLOR,
        fg='#00A2E8',
        font=(None, 40, 'bold'),
    )


def notify(
    message: str,
    destory_ms: int = 1000,
    font_color: str = '#00A2E8',
    font_size: int = 40,
    font_weight: str = 'bold',
):
    notification_window = create_notification_window()
    label = Label(
        notification_window,
        text=message,
        bg=TRANSPARENT_COLOR,
        fg=font_color,
        font=(None, font_size, font_weight),
    )
    label.pack()

    notification_window.update()

    move_window_to_screen_center(notification_window)

    if destory_ms:
        notification_window.after(destory_ms, notification_window.destroy)

    notification_window.mainloop()


def countdown(window, label, seconds):
    if seconds == 0:
        window.destroy()
    else:
        label['text'] = seconds
        window.after(1000, countdown, window, label, seconds - 1)


def notify_countdown(seconds: int):
    notification_window = create_notification_window()
    move_window_to_screen_center(notification_window)

    label = default_label('倒计时即将开始')
    label.pack()
    notification_window.after(
        1000,
        countdown,
        notification_window,
        label,
        seconds,
    )
    notification_window.mainloop()
