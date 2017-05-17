import tkinter as tk
import tkinter.font as font
import tkinter.scrolledtext as scrolledtext
import tkinter.messagebox as messagebox
import tkinter.filedialog as filedialog
from tkinter import ttk

import gui_clusterize
import gui_fetch
import gui_empty
import gui_new_project
import sys

window = None


class MyStream(object):
    def __init__(self, target):
        self.target = target

    def write(self, s):
        if window is not None and False:
            window.print_log(s)
        self.target.write(s)


class Window:
    def __init__(self):
        global window
        window = self
        self.log = None
        self.data = None
        self.root = None
        self.pages = {
            'new_project': None,
            'clustering': None,
            'fetch': None,
            'empty': None,
        }
        self.project_name = None
        self.filemenu = None
        self.projectmenu = None
        self.init_controls()

    def init_controls(self):
        self.root = tk.Tk()
        self.root.geometry("800x500")
        self.root.title("Smart checker")
        self.root.resizable(True, True)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0, minsize=80)

        menu = tk.Menu(self.root)
        self.filemenu = tk.Menu(menu)
        self.filemenu.add_command(label='New project', command=self.new_project)
        self.filemenu.add_command(label='Open project', command=self.open_project)
        self.filemenu.add_command(label='Save', command=lambda: self.save_project(None), state=tk.DISABLED)
        self.filemenu.add_command(label='Save as', command=self.save_project_as, state=tk.DISABLED)
        self.filemenu.add_separator()
        self.filemenu.add_command(label="Exit", command=self.close_window)
        self.root.protocol("WM_DELETE_WINDOW", self.close_window)

        self.projectmenu = tk.Menu(menu)
        self.projectmenu.add_command(label='Upgrade', command=self.upgrade, state=tk.DISABLED)

        menu.add_cascade(label="File", menu=self.filemenu)
        menu.add_cascade(label="Project", menu=self.projectmenu)
        self.root.config(menu=menu)

        self.logframe = tk.Frame(self.root, borderwidth=1, relief="sunken")
        self.logframe.grid(column=0, row=1, sticky="sew", pady=(0, 20), padx=(40, 40))

        self.log = scrolledtext.ScrolledText(self.logframe, height=5, selectborderwidth=0, highlightthickness=0)
        self.log.pack(fill='both')
        self.log.configure(state='disabled')
        self.log.bind("<1>", lambda event: self.log.focus_set())

        self.print_log("Log:")

        self.empty_page()

        self.root.mainloop()

    def print_log(self, text):
        self.log.configure(state='normal')
        self.log.insert('end', text + '\n')
        self.log.configure(state='disabled')

    def new_project(self):
        self.clear_pages()

        def set_commands():
            self.filemenu.entryconfigure(0, state=tk.ACTIVE)
            self.filemenu.entryconfigure(1, state=tk.ACTIVE)
            self.filemenu.entryconfigure(2, state=tk.DISABLED)
            self.filemenu.entryconfigure(3, state=tk.DISABLED)
            self.projectmenu.entryconfigure(0, state=tk.DISABLED)

        self.pages['new_project'] = gui_new_project.NewProjectPage(self, self.root, set_commands)
        self.pages['new_project'].grid(column=0, row=0, sticky="nsew", pady=(0, 0), padx=(100, 100))

    def show_fetch(self, sources, tests):
        self.clear_pages()

        def set_commands():
            self.filemenu.entryconfigure(0, state=tk.DISABLED)
            self.filemenu.entryconfigure(1, state=tk.DISABLED)
            self.filemenu.entryconfigure(2, state=tk.ACTIVE)
            self.filemenu.entryconfigure(3, state=tk.ACTIVE)
            self.projectmenu.entryconfigure(0, state=tk.DISABLED)

        self.pages['fetch'] = gui_fetch.FetchPage(self, self.root, set_commands, sources, tests)
        self.pages['fetch'].grid(column=0, row=0, sticky="nsew", pady=(0, 0), padx=(100, 100))

    def open_project(self, project=None):
        self.clear_pages()
        self.data = project

        def set_commands():
            self.filemenu.entryconfigure(0, state=tk.ACTIVE)
            self.filemenu.entryconfigure(1, state=tk.ACTIVE)
            self.filemenu.entryconfigure(2, state=tk.ACTIVE)
            self.filemenu.entryconfigure(3, state=tk.ACTIVE)
            self.projectmenu.entryconfigure(0, state=tk.ACTIVE)

        self.pages['clustering'] = gui_clusterize.ClusterizePage(self, self.root, set_commands)
        self.pages['clustering'].grid(column=0, row=0, sticky="nsew", pady=(0, 0), padx=(0, 40))

    def empty_page(self):
        self.clear_pages()

        def set_commands():
            self.filemenu.entryconfigure(0, state=tk.ACTIVE)
            self.filemenu.entryconfigure(1, state=tk.ACTIVE)
            self.filemenu.entryconfigure(2, state=tk.DISABLED)
            self.filemenu.entryconfigure(3, state=tk.DISABLED)
            self.projectmenu.entryconfigure(0, state=tk.DISABLED)

        self.pages['empty'] = gui_empty.EmptyPage(self, self.root, set_commands)
        self.pages['empty'].grid(column=0, row=0, sticky="nsew", pady=(100, 0), padx=(0, 0))

    @staticmethod
    def show_loading(title):
        loading = tk.Toplevel()
        loading.title(title)

        label = tk.Label(loading, font=font.Font(family='Helvetica', size=36), text='Loading')
        label.pack(side='top', padx=20, pady=(40, 10))

        bar = ttk.Progressbar(loading, mode='indeterminate')
        bar.start()
        bar.pack(side='bottom', padx=20, pady=(10, 40))
        return loading

    def save_project_as(self):
        file = filedialog.asksaveasfile(mode='w')

        if file is None:
            return

        self.save_project(file)

    def save_project(self, file):

        if file is not None:
            self.data.output = file

        self.data.save()
        self.print_log('Saved')

    def upgrade(self):
        pass

    def clear_pages(self):
        self.data = None
        for name, page in self.pages.items():
            if page is not None:
                print("destroying {} {}".format(name, page))
                page.grid_forget()
                #page.destroy()
                self.pages[name] = None

    def close_window(self):
        print('close_window')
        if self.data is not None:
            if self.data.is_changed:
                if messagebox.askyesno("Save?", "Project has been changed. Save?"):
                    self.data.save()

        sys.stdout.flush()
        self.root.quit()


def main():
    window = Window()
