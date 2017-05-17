import tkinter as tk
import tkinter.font as font
import FileChooseLine
import os


class NewProjectPage(tk.Frame):
    def __init__(self, main, root, callback):
        super().__init__(root)
        self.main = main
        self.init_controls(callback)

    def init_controls(self, callback):

        callback()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=3)
        self.rowconfigure(1, weight=0)
        self.rowconfigure(2, weight=0)
        self.rowconfigure(3, weight=0)
        self.rowconfigure(4, weight=1)
        self.rowconfigure(5, weight=3)

        label_size = max(len('Choose source codes:'), len('Choose tests:'), len('Project name')) - 3

        fr = tk.Frame(self)
        fr.columnconfigure(0, weight=0)
        fr.columnconfigure(1, weight=1)
        fr.rowconfigure(0, weight=1)
        l_name = tk.Label(fr, text='Project name:', anchor='e', width=label_size)
        l_name.grid(column=0, row=0)
        self.name = tk.Entry(fr)
        self.name.grid(column=1, row=0, sticky='nsew')

        fr.grid(column=0, row=1, sticky='ew')

        self.sources = FileChooseLine.FileChooseLine(self,
                                                     label_size=label_size,
                                                     text='Choose source codes:',
                                                     title='Choose folder with source codes',
                                                     is_dir=True,
                                                     path=os.path.dirname(__file__))
        self.sources.grid(column=0, row=2, sticky='ew')
        self.tests = FileChooseLine.FileChooseLine(self,
                                                     label_size=label_size,
                                                     text='Choose tests:',
                                                     title='Choose folder with tests',
                                                     is_dir=True,
                                                     path=os.path.dirname(__file__))
        self.tests.grid(column=0, row=3, sticky='ew')

        self.button = tk.Button(self, text='Start', command=self.start)
        self.button.grid(column=0, row=4, sticky='se')

    def start(self):

        self.main.show_fetch(self.name.get(), self.sources.get(), self.tests.get())
        #self.main.root.after(1, lambda: self.main.show_fetch(self.sources.get(), self.tests.get()))

