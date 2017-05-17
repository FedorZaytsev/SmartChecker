import os
import datetime
import json
import fetch
import project
import threading
import tkinter as tk
from tkinter import ttk
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox


def prett_timedelta(td):
    def delta(tdelta):
        d = {"days": tdelta.days}
        d["hours"], rem = divmod(tdelta.seconds, 3600)
        d["minutes"], d["seconds"] = divmod(rem, 60)
        d['hours'] += d['days']*24
        d['days'] = 0
        return d

    d = delta(td)
    mins = str(d['minutes'])
    mins = mins if len(mins) > 1 else '0' + mins
    arr = [str(d['hours']), mins, '00']

    return ':'.join(arr)


class FetchPage(tk.Frame):
    def __init__(self, main, root, callback, sources, tests):
        self.main = main
        super().__init__(root)
        self.startTime = datetime.datetime.now()
        self.sources_folder = sources
        self.tests_folder = tests
        self.textbox = None
        self.savefile = None
        self.progress_bar = None
        self.progress_test = None
        self.progress_label = None
        self.estimated_time_box = None
        self.progress_test_label = None
        self.prev_timedelta = None
        self.curr_timedelta = None
        self.estimated_time_coef = 0.002
        self.current_user_idx = 0
        self.init_controls(callback)

    def init_controls(self, callback):
        self.savefile = filedialog.asksaveasfilename(title='Choose file to save in')
        if self.savefile == "":
            return

        callback()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=3)
        self.rowconfigure(1, weight=0)
        self.rowconfigure(2, weight=0)
        self.rowconfigure(3, weight=0)
        self.rowconfigure(4, weight=0)
        self.rowconfigure(5, weight=0)
        self.rowconfigure(6, weight=1)
        self.rowconfigure(7, weight=3)

        self.progress_label = tk.Label(self, text='Processed zero solutions')
        self.progress_label.grid(row=1, column=0)

        self.progress_bar = ttk.Progressbar(self, length=400)
        self.progress_bar.grid(row=2, column=0, sticky='ew')

        self.textbox = tk.Label(self, height=2)
        self.textbox.grid(row=3, column=0, pady=(20, 0))
        self.textbox.config(text="Preparing for running tests")

        self.progress_test = ttk.Progressbar(self, length=400)
        self.progress_test.grid(row=4, column=0, sticky='ew')

        self.estimated_time_box = tk.Label(self)
        self.estimated_time_box.grid(row=5, column=0)
        self.estimated_time_box.config(text="Estimated time: calculating...")

        self.pause_btn = tk.Button(self, text='Pause', command=self.fetch_pause)
        self.pause_btn.grid(row=6, column=0, sticky='e', pady=(20, 0))

        t = threading.Thread(name='fetch.check_folder', target=self.test_task_continue)
        t.start()

    @staticmethod
    def shorten_path(path):
        max_len = 60
        if len(path) > max_len:
            path = path[:max_len//2] + '...' + path[-max_len//2:]
        return path

    def step(self, idx, size, name):
        self.current_user_idx = idx
        self.progress_bar['value'] = idx
        self.progress_bar['maximum'] = size-1
        self.textbox.config(text="Testing {}".format(self.shorten_path(os.path.basename(name['file']))))
        self.progress_label.config(text="Processed {} of {}".format(idx + 1, size))

    def step_test(self, idx, size, overall_count):
        self.progress_test['value'] = idx
        self.progress_test['maximum'] = size-1

        self.estimated_time_box.config(text=self.calculate_estimated_time(idx, size, overall_count))

    def calculate_estimated_time(self, idx, size, overall_count):
        seconds_passed = (datetime.datetime.now() - self.startTime).total_seconds()
        if seconds_passed >= 10 and idx > 0:
            time = seconds_passed / (self.current_user_idx * size + idx) * overall_count
            timedelta = datetime.timedelta(seconds=time - seconds_passed)
            if self.prev_timedelta is None:
                self.prev_timedelta = timedelta
            else:
                self.prev_timedelta = self.curr_timedelta

            timedelta = (timedelta - self.prev_timedelta)*self.estimated_time_coef + self.prev_timedelta
            self.curr_timedelta = timedelta

            self.estimated_time_box.config(
                text="Estimated time: ~ {}".format(prett_timedelta(timedelta)))

    def test_task_continue(self):
        self.startTime = datetime.datetime.now()
        self.main.data = project.Project(output=self.savefile)
        fetch.check_folder(self.sources_folder,
                           self.tests_folder,
                           self.step,
                           self.step_test,
                           self.main.print_log,
                           self.main.data)

        self.main.data.save()

        self.main.open_project(self.main.data)

        print("test_task end")

    def fetch_pause(self):
        if fetch.is_running.is_set():
            fetch.is_running.clear()
            self.pause_btn.config(text='Continue')
        else:
            fetch.is_running.set()
            self.pause_btn.config(text='Pause')
