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
    def __init__(self, main, root, callback):
        self.main = main
        super().__init__(root)
        self.startTime = datetime.datetime.now()
        self.textbox = None
        self.savefile = None
        self.directory = None
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
        self.directory = filedialog.askdirectory(title='Choose folder with task')
        if self.directory == "":
            return

        self.savefile = filedialog.asksaveasfile(mode='w', title='Choose file to save in')
        if self.savefile is None:
            return

        callback()

        self.columnconfigure(0, weight=1)

        self.progress_label = tk.Label(self, text='Progress:')
        self.progress_label.grid(row=0, column=0)

        self.progress_bar = ttk.Progressbar(self, length=400)
        self.progress_bar.grid(row=1, column=0, sticky='ew')

        self.textbox = tk.Label(self, height=2)
        self.textbox.grid(row=2, column=0, pady=(20, 0))
        self.textbox.config(text="Preparing for running tests")

        self.progress_test = ttk.Progressbar(self, length=400)
        self.progress_test.grid(row=3, column=0, sticky='ew')

        self.estimated_time_box = tk.Label(self)
        self.estimated_time_box.grid(row=4, column=0)
        self.estimated_time_box.config(text="Estimated time: calculating...")

        t = threading.Thread(name='fetch.check_folder', target=self.test_task_continue)
        t.start()

    def step(self, idx, size, name):
        self.current_user_idx = idx
        self.progress_bar['value'] = idx
        self.progress_bar['maximum'] = size-1
        self.textbox.config(text="Testing\n{}".format(os.path.basename(name['file'])))
        self.progress_label.config(text="{}/{}".format(idx + 1, size))

    def step_test(self, idx, size, overall_count):
        self.progress_test['value'] = idx
        self.progress_test['maximum'] = size-1
        #self.progress_test_label.config(text="Testing: {}/{}".format(idx + 1, size))

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

            print("estimated", timedelta)
            timedelta = (timedelta - self.prev_timedelta)*self.estimated_time_coef + self.prev_timedelta
            print("showed", timedelta)
            self.curr_timedelta = timedelta

            self.estimated_time_box.config(
                text="Estimated time: ~ {}".format(prett_timedelta(timedelta)))

    def test_task_continue(self):
        self.startTime = datetime.datetime.now()
        self.main.data = project.Project(output=self.savefile)
        fetch.check_folder(self.directory, self.step, self.step_test, self.main.print_log, self.main.data)

        self.main.data.save()
        #messagebox.showinfo(title='Saved', message='Done!')

        self.main.open_project()

        print("test_task end")
