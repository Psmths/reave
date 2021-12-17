import time
from queue import Queue


class Agent():
    """
    Agent class holds stateful data about an agent.
    """
    def __init__(self, listener, uuid, lastseen):
        self.listener = listener
        self.uuid = uuid
        self.command_queue = Queue()
        self.payload_queue = Queue()
        self.lastseen = lastseen

    def update_lastseen(self):
        self.lastseen = time.time()

    def add_command(self, command):
        self.command_queue.put(command)

    def add_payload(self, payload_script):
        self.payload_queue.put(payload_script)

    def get_command(self):
        if self.command_queue.empty():
            return False
        else:
            return self.command_queue.get()

    def get_payload(self):
        if self.payload_queue.empty():
            return False
        else:
            return self.payload_queue.get()
