import tkinter as tk
import tkinter.font as font


class EmptyPage(tk.Frame):
    def __init__(self, main, root, callback):
        super().__init__(root)
        self.main = main
        self.init_controls(callback)

    def init_controls(self, callback):

        callback()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        info_label = tk.Label(self, text="Use 'File' → 'New project' to start",
                              font=font.Font(family='Helvetica', size=20), foreground='#808080')
        info_label.grid(row=0, column=0, sticky='nsew')

