import os
import time
import subprocess
import ListboxEx
import tkinter as tk
import tkinter.font as font
from settings import *
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import figure
import tkinter.scrolledtext as scrolledtext


class ClusterWindow(tk.Toplevel):
    def __init__(self, data, idx, main):
        super().__init__()

        self.idx = idx
        self.main = main
        self.project = data
        self.data = data.get_cluster(idx)
        self.cluster_info = data.get_cluster_info(idx)
        self.solutions = None
        self.plot_frame = None
        self.space_frame = None
        self.solutions = None
        self.doubleClickTime = time.clock()

        self.y_max = 0
        for solution in self.data:
            self.y_max = max(self.y_max, max(solution.times))

        self.init_controls()
        self.title(self.cluster_info['name'])

        self.protocol("WM_DELETE_WINDOW", self.on_destroy)

    def on_destroy(self):
        self.main.on_solution_close(self.idx)
        self.destroy()

    def init_controls(self):
        def updateName(val):
            self.title(val)
            self.main.clusters.delete(self.idx)
            self.main.clusters.insert(self.idx, "{} ({})".format(val, len(self.data)))
            self.project.clusters[self.idx]['name'] = val
            self.project.is_changed = True
            return True

        def updateDescription(val):
            self.project.clusters[self.idx]['description'] = val
            self.project.is_changed = True
            return True

        fr1 = tk.Frame(self)
        fr1.grid(row=0, column=0, padx=(60, 0))
        label_name = tk.Label(fr1, font=font.Font(family='Helvetica', size=14), text='Name:')
        label_name.grid(row=0, column=0, sticky='e')

        name_input = tk.Entry(fr1, exportselection=0, validate='key',
                                     validatecommand=(self.register(updateName), '%P'))
        name_input.insert(tk.END, self.cluster_info['name'])
        name_input.grid(row=0, column=1)

        label_description = tk.Label(fr1, font=font.Font(family='Helvetica', size=14), text='Description:')
        label_description.grid(row=1, column=0, sticky='e')

        desc_input = tk.Entry(fr1, exportselection=0, validate='key',
                                     validatecommand=(self.register(updateDescription), '%P'))
        desc_input.insert(tk.END, self.cluster_info['description'])
        desc_input.grid(row=1, column=1)

        self.solutions = ListboxEx.ListboxEx(fr1, height=15)
        self.solutions.grid(row=2, column=0, columnspan=2, sticky='nsew')

        self.plot_frame = tk.Frame(self)
        self.plot_frame.grid(row=0, column=2)

        self.show_plot(self.plot_frame, 0)
        self.update()
        self.minsize(self.winfo_width(), self.winfo_height())

        def on_copy():
            idx = self.solutions.curselection()[0]
            text = self.data[idx]['name']['file']
            _, text = os.path.split(text)
            self.clipboard_clear()
            self.clipboard_append(text)

        popup = tk.Menu(self.solutions, tearoff=0)
        popup.add_command(label="Copy", command=lambda: on_copy())

        for solution in self.data:
            meta = solution.meta
            self.solutions.insert(tk.END, '{} {}'.format(meta['username'], meta['date']))

        self.solutions.selection_set(0)

        def on_right_click(event):
            widget = event.widget
            index = widget.nearest(event.y)
            _, yoffset, _, height = widget.bbox(index)
            if event.y > height + yoffset + 5:  # XXX 5 is a niceness factor :)
                # Outside of widget.
                return
            item = widget.get(index)
            popup.post(event.x_root, event.y_root)

        self.solutions.bind('<Double-Button-1>', lambda e: self.on_solution_clicked())
        self.solutions.bind('<<ListboxSelect>>', lambda e: self.on_solution_selected_fake())
        self.solutions.bind("<Button-2>", lambda event: on_right_click(event))
        self.bind('<Key>', lambda e: self.on_keypressed(e))

    def on_keypressed(self, e):
        if e.keysym == 'Up':
            cur = self.solutions.curselection()
            if len(cur) == 1 and cur[0] > 0:
                self.solutions.selection_clear(cur[0])
                self.solutions.selection_set(cur[0] - 1)
                self.solutions.see(cur[0] - 1)
                self.on_solution_selected()
        elif e.keysym == 'Down':
            cur = self.solutions.curselection()
            if len(cur) == 1 and cur[0] < self.solutions.size()-1:
                self.solutions.selection_clear(cur[0])
                self.solutions.selection_set(cur[0] + 1)
                self.solutions.see(cur[0] + 1)
                self.on_solution_selected()

    def on_solution_selected_fake(self):
        self.after(200, lambda: self.is_solo_click())

    def is_solo_click(self):
        if time.clock() - self.doubleClickTime > 0.005:
            self.on_solution_selected()

    def on_solution_selected(self):
        if len(self.solutions.curselection()) == 0:
            return

        idx = self.solutions.curselection()[0]
        self.show_plot(self.plot_frame, idx)

    def show_plot(self, frame, idx):
        for window in frame.winfo_children():
            window.destroy()

        f = figure.Figure(figsize=(6, 4), dpi=100)
        canvas = FigureCanvasTkAgg(f, master=frame)
        a = f.add_subplot(111)
        a.set_ylim([-1, self.y_max+1])
        times = self.data[idx].times
        a.scatter([i+1 for i in range(len(times))], [e for e in times], c='red', marker='o', s=16)
        a.set_title('Time passed on different tests')
        a.set_xlabel('Test id')
        a.set_ylabel('Time in ms')
        canvas.show()
        canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        canvas._tkcanvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

    def on_solution_clicked(self):
        self.doubleClickTime = time.clock()
        if len(self.solutions.curselection()) == 0:
            return

        idx = self.solutions.curselection()[0]
        self.solutions.activate(idx)
        subprocess.call([config['view']['editor_cmd'], self.data[idx].filepath])


