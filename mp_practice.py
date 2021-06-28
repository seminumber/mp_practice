import multiprocessing as mp
import tkinter as tk
import mp_worker as worker


class MultiStateButton(tk.Button):
    def __init__(self, master, configs=None):
        if configs is None:
            configs = [{"state": tk.NORMAL}]

        self.configs = configs
        self.state_idx = 0
        self._command = None
        config = self.get_updated_command(configs[0])
        super().__init__(master, **config)

    def get_updated_command(self, config):
        config_out = config.copy()
        self._command = config_out.get("command", None)
        config_out["command"] = self._button_command
        return config_out

    def move_next_state(self):
        self.state_idx = (self.state_idx + 1) % len(self.configs)

        self.config(**self.configs[self.state_idx])

    def _button_command(self):
        if self._command is not None:
            self._command()


class DoEchoButton(MultiStateButton):
    def __init__(self, master, command, cancel_command):
        configs = [
            {
                "text": "Echo",
                "foreground": "black",
                "command": command,
                "state": tk.NORMAL,
            },
            {
                "text": "Cancel Echo",
                "foreground": "red",
                "command": cancel_command,
                "state": tk.NORMAL
            },
            {
                "text": "Cancelling...",
                "command": tk.NONE,
                "state": tk.DISABLED,
            }
        ]
        super().__init__(master, configs)


class MainWindow(tk.Frame):
    def __init__(self, master, pipe):
        super().__init__(master)
        self.label = tk.Label(self, text="Simple task")
        self.button = DoEchoButton(self, command=self.button_command, cancel_command=self.cancel_command)
        self.label.pack()
        self.button.pack()
        self.text1 = tk.Text(self, height=160, width=400)
        self.output_lines = ["Initialize MainWindow..."]
        self.text1.insert(tk.END, "\n".join(self.output_lines))
        self.text1.pack()
        self.line_num = 0

        self.pipe: mp.connection.PipeConnection = pipe
        self.after(250, self.message_loop)

    def button_command(self):
        self.pipe.send({
            "command": "echo",
            "data": "sample message"
        })
        self.button.move_next_state()

    def cancel_command(self):
        self.pipe.send({
            "command": "cancel",
            "data": {"timeout": 10}
        })
        self.button.move_next_state()


    def message_loop(self):
        if self.pipe.poll():
            msg = self.pipe.recv()
            self.output_lines.append(f"[{self.line_num}] Received {msg}")
            self.line_num += 1
            self.refresh_text()
            if msg == "cancelled":
                self.button.move_next_state()
            # messagebox.showinfo(title="Received", message=msg)

        self.after(250, self.message_loop)

    def refresh_text(self):
        text = "\n".join(self.output_lines[-10:])
        self.text1.delete("1.0", tk.END)
        self.text1.insert(tk.END, text)


class App(tk.Tk):
    def __init__(self, pipe):
        super().__init__()
        window_size = (320, 160)
        self.geometry("{}x{}".format(*window_size))
        self.frame = MainWindow(self, pipe)
        self.frame.pack()


if __name__ == "__main__":
    worker_pipe, gui_pipe = mp.Pipe()
    wp = worker.WorkerProcess(worker_pipe, daemon=True)
    wp.start()
    try:
        App(gui_pipe).mainloop()
    finally:
        wp.terminate()
