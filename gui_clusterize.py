import numpy as np
import json
import fetch
import time
import threading
import clustering
import tkinter as tk
import tkinter.filedialog as filedialog
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import figure
import project

import gui_cluster


class ClusterizePage(tk.Frame):
    def __init__(self, main, root, callback):
        self.main = main
        self.mask = None
        self.labels = None
        self.clusters = None
        self.filename = None
        self.spaceframe = None
        self.clusteringframe = None
        self.doubleClickTime = time.clock()
        self.cluster_views = []
        super().__init__(root)
        self.load_statistic(callback)

    def load_statistic(self, callback):
        self.filename = filedialog.askopenfilename()

        if self.filename == '':
            return

        loading = self.main.show_loading("Loading...")
        callback()

        def load_stat_thread():
            with open(self.filename, 'r') as file:
                self.main.data = project.Project(file=file)
            self.main.data.drop_rt()
            #self.main.data.drop_tl()
            #self.main.data.drop_test_failed()
            print("Loaded {} elements".format(self.main.data.size()))
            self.draw_data()
            self.redraw()
            #self.fill_clusters()
            #self.cluster_views = [None for i in range(len(self.main.data.clusters))]

            print("loaded")
            self.main.print_log('loaded {} solutions'.format(self.main.data.size()))
            loading.destroy()

        t = threading.Thread(name='load_statistic', target=load_stat_thread)
        t.start()

    def draw_space(self, root):
        if self.spaceframe is not None:
            self.spaceframe.destroy()
            self.spaceframe = None

        self.spaceframe = tk.Frame(root)
        f = figure.Figure(figsize=(6, 4), dpi=100)
        canvas = FigureCanvasTkAgg(f, master=self.spaceframe)
        a = f.add_subplot(111, projection='3d')

        colors = clustering.generate_colors(self.main.data.cluster_count())

        # Times
        #print('mask', self.mask)
        dimensions = self.main.data.get_dimentions()
        #print('labels', np.unique(self.main.data.get_labels()))
        #print('mask', self.mask)
        print('clusters', np.unique(self.main.data.get_labels()))
        for idx, label in enumerate(np.unique(self.main.data.get_labels())):

            time = self.main.data.get_times_by_test(idx)
            print("times", time)
            assert idx < len(colors)
            assert idx < len(self.mask)
            off = self.main.data.skip_count
            a.scatter(xs=time[dimensions[0]['i']-off], ys=time[dimensions[1]['i']-off], zs=time[dimensions[2]['i']-off],
                      c=colors[idx], marker='o', s=16, alpha=self.mask[idx])

        a.set_title('Time')
        a.set_xlabel('test {}'.format(dimensions[0]['i']))
        a.set_ylabel('test {}'.format(dimensions[1]['i']))
        a.set_zlabel('test {}'.format(dimensions[2]['i']))

        canvas.show()
        canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        canvas._tkcanvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

    def clusterize(self, count):
        self.main.data.clusterize(count)
        self.redraw()

    def redraw(self):
        self.destroy_cluster_views()
        self.cluster_views = [None for _ in range(self.main.data.cluster_count())]
        self.mask = [1 for _ in range(self.main.data.cluster_count())]

        self.fill_clusters()
        self.redraw_plot()

    def redraw_plot(self):
        self.draw_space(self.clusteringframe)
        self.spaceframe.pack(side=tk.LEFT, expand=1)

    def destroy_cluster_views(self):
        for el in self.cluster_views:
            if el is not None:
                el.destroy()

    def draw_data(self):

        if self.clusteringframe is not None:
            self.clusteringframe.destroy()
            self.clusteringframe = None

        self.clusteringframe = tk.Frame(self)
        self.clusteringframe.pack(expand=1, fill=tk.BOTH)

        dimentions = self.main.data.get_dimentions()
        print("dimentions {}...".format(dimentions[:3]))

        def isNumber(val):
            if val == "":
                return True
            try:
                int(val)
                return True
            except ValueError:
                return False

        self.frame_clusters = tk.Frame(self.clusteringframe)
        self.frame_clusters.pack(side=tk.RIGHT, expand=1)
        label_cluster_info = tk.Label(self.frame_clusters, text="Maximum count of clusters:")
        label_cluster_info.pack()
        textedit_clusters = tk.Entry(self.frame_clusters, exportselection=0, validate='key',
                                     validatecommand=(self.frame_clusters.register(isNumber), '%P'))
        textedit_clusters.insert(tk.END, str(len(self.main.data.clusters)))
        textedit_clusters.pack()
        button_start = tk.Button(self.frame_clusters, text='Clusterize',
                                 command=lambda: self.clusterize(int(textedit_clusters.get())))
        button_start.pack()

        self.clusters = tk.Listbox(self.frame_clusters)
        self.clusters.pack(expand=1)
        self.clusters.bind('<Double-Button-1>', lambda e: self.on_solution_clicked())
        self.clusters.bind('<<ListboxSelect>>', lambda e: self.on_solution_selected_fake())

    def on_focus_out(self):
        print('focus_out')
        self.mask = [1 for i in range(len(self.mask))]
        self.redraw_plot()

    def on_solution_selected_fake(self):
        self.after(200, lambda: self.is_solo_click())

    def is_solo_click(self):
        if time.clock() - self.doubleClickTime > 0.005:
            self.on_solution_selected()

    def on_solution_selected(self):
        if len(self.clusters.curselection()) == 0:
            return

        idx = self.clusters.curselection()[0]
        self.mask = [0.1 for i in range(len(self.mask))]
        self.mask[idx] = 1
        self.redraw_plot()

    def fill_clusters(self):
        if self.clusters.size() > 0:
            self.clusters.delete(0, self.clusters.size()-1)

        for cluster in self.main.data.clusters:
            self.clusters.insert(tk.END, '{} ({})'.format(cluster['name'], len(cluster['elements'])))


    def on_solution_close(self, idx):
        self.cluster_views[idx] = None

    def on_solution_clicked(self):
        self.doubleClickTime = time.clock()
        if len(self.clusters.curselection()) == 0:
            return
        idx = self.clusters.curselection()[0]
        #print("event", idx)

        if self.cluster_views[idx] is not None:
            self.cluster_views[idx].lift()
            self.cluster_views[idx].focus_force()
        else:
            self.cluster_views[idx] = gui_cluster.ClusterWindow(self.main.data, idx, self)
