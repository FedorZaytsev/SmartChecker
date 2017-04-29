import os
import datetime
import json
import fetch
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
        self.current_user_idx = 0
        self.test_task(callback)

    def test_task(self, callback):
        self.directory = filedialog.askdirectory(title='Choose folder with task')
        if self.directory == "":
            return

        self.savefile = filedialog.asksaveasfile(mode='w', title='Choose file to save in')
        if self.savefile is None:
            return

        callback()

        mainframe = tk.Frame(self)
        mainframe.pack(side='top', pady=(80, 20))

        tk.Label(mainframe, text='Progress:').grid(row=1, column=1)

        self.progress_bar = ttk.Progressbar(mainframe, length=400)
        self.progress_bar.grid(row=2, column=1)

        self.progress_label = tk.Label(mainframe)
        self.progress_label.grid(row=2, column=2)

        self.textbox = tk.Label(mainframe)
        self.textbox.grid(row=3, column=1, pady=(20, 0))
        self.textbox.config(text="Preparing for running tests")

        self.progress_test = ttk.Progressbar(mainframe, length=400)
        self.progress_test.grid(row=4, column=1)

        self.progress_test_label = tk.Label(mainframe, width=10)
        self.progress_test_label.grid(row=4, column=2)

        self.estimated_time_box = tk.Label(mainframe)
        self.estimated_time_box.grid(row=5, column=1)
        self.estimated_time_box.config(text="Estimated time: calculating...")

        t = threading.Thread(name='fetch.check_folder', target=self.test_task_continue)
        t.start()

    def step(self, idx, size, name):
        self.current_user_idx = idx
        self.progress_bar['value'] = idx
        self.progress_bar['maximum'] = size
        self.textbox.config(text="Testing {}".format(os.path.basename(name['file'])))
        self.progress_label.config(text="{}/{}".format(idx + 1, size))

    def step_test(self, idx, size, overall_count):
        self.progress_test['value'] = idx
        self.progress_test['maximum'] = size
        self.progress_test_label.config(text="{}/{}".format(idx + 1, size))
        seconds_passed = (datetime.datetime.now() - self.startTime).total_seconds()
        if seconds_passed >= 10 and idx > 0:
            time = seconds_passed / (self.current_user_idx*size + idx) * overall_count

            self.estimated_time_box.config(
                text="Estimated time: ~ {}".format(prett_timedelta(datetime.timedelta(seconds=time))))

    def test_task_continue(self):
        self.startTime = datetime.datetime.now()
        self.main.data = fetch.check_folder(self.directory, self.step, self.step_test,
                                            self.main.print_log,
                                            )


        messagebox.showinfo(title='Saved', message='Done!')

        json.dump(self.main.data, self.savefile, sort_keys=True, indent=4)

        print("test_task end")
