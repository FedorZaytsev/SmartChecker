import tkinter as tk
import tkinter.filedialog as filedialog


class FileChooseLine(tk.Frame):
    def __init__(self, master=None, **kw):
        filename = kw.pop('path', '')
        self.is_dir = kw.pop('is_dir', False)
        self.title = kw.pop('title', None)
        text = kw.pop('text', 'NO TEXT')
        label_size = kw.pop('label_size', None)

        tk.Frame.__init__(self, master, **kw)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=0)
        self.rowconfigure(0, weight=1)
        self.entry = tk.Entry(self)
        self.entry.insert(0, filename)
        self.entry.grid(column=1, row=0, sticky='ew')

        self.btn = tk.Button(self, text='Choose..',
                             command=self.choose_clicked)
        self.btn.grid(column=2, row=0)

        self.text = tk.Label(self, text=text, width=label_size, anchor='e')
        self.text.grid(column=0, row=0)
        self.entry.xview_moveto(1.0)

    def choose_clicked(self):
        filename = ''
        if self.is_dir:
            filename = filedialog.askdirectory(initialdir=self.entry.get(), title=self.title)
        else:
            filename = filedialog.askopenfilename(initialfile=self.entry.get(), title=self.title)
        self.entry.delete(0, 'end')
        self.entry.insert(0, filename)
        self.entry.xview_moveto(1.0)

    def get(self):
        return self.entry.get()

