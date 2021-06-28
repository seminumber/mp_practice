import multiprocessing as mp
import asyncio


class CancellationToken:
    cancel = False


class BackgroundWorkerAsync:
    def __init__(self, pipe, event_loop):
        self.pipe: mp.connection.PipeConnection = pipe
        self.refresh_rate = 0.25  # in sec
        self.cancellation_token = None
        self.event_loop = event_loop

    async def run(self):
        while True:
            while self.pipe.poll():
                msg = self.pipe.recv()
                print(msg)
                command = msg["command"]
                data = msg["data"]
                self.process_msg(command, data)
            await asyncio.sleep(self.refresh_rate)

    def process_msg(self, command: str, data):
        # logger = logging.getLogger("process_msg")
        if command == "echo":
            if self.cancellation_token is not None:
                self.cancellation_token.cancel = True
            self.cancellation_token = CancellationToken()
            self.event_loop.create_task(self.echo_loop(data, self.cancellation_token))
        elif command == "cancel":
            if self.cancellation_token is not None:
                self.cancellation_token.cancel = True
            self.cancellation_token = None
        else:
            print("unrecognized command", command)
            # logger.error("Unrecognized command", command)
            return None

    async def echo_loop(self, data, cancellation_token):
        while not cancellation_token.cancel:
            self.pipe.send(data)
            await asyncio.sleep(self.refresh_rate * 10)
        self.pipe.send("cancelled")


class WorkerProcess(mp.Process):
    def __init__(self, pipe, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pipe = pipe

    def run(self):
        event_loop = asyncio.get_event_loop()
        worker = BackgroundWorkerAsync(self.pipe, event_loop)
        event_loop.create_task(worker.run())
        event_loop.run_forever()
