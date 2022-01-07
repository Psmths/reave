import time
import json
import datetime
from queue import Queue


class Agent:
    """
    Agent class holds stateful data about an agent.
    """

    def __init__(self, listener, uuid, lastseen, enumdata):
        self.listener = listener
        self.uuid = uuid
        self.command_queue = Queue()
        self.payload_queue = Queue()
        self.task_queue = Queue()
        self.lastseen = lastseen
        self.enumdata = enumdata

    def beacon_expired(self):
        """
        Returns true if the beacon was expected, but was not received in a
        timely manner.
        """
        agent_options_dict = json.loads(self.enumdata["agent_options"])
        start_time = agent_options_dict["START_TIME"]
        end_time = agent_options_dict["END_TIME"]
        start_time = datetime.time(*map(int, start_time.split(":")))
        end_time = datetime.time(*map(int, end_time.split(":")))
        max_beacon_interval = (
            agent_options_dict["BEACON_INTERVAL"] + agent_options_dict["BEACON_JITTER"]
        )
        if start_time <= datetime.datetime.now().time() < end_time:
            if time.time() - max_beacon_interval > self.lastseen:
                return True
        return False

    def get_platform(self):
        """
        Returns the reported platform for the agent.
        """
        return self.enumdata["host_data"]["host_platform"]

    def get_hostname(self):
        """
        Returns the reported hostname for the agent.
        """
        return self.enumdata["host_data"]["host_name"]

    def update_lastseen(self):
        """
        Updates the agent's last seen time.
        """
        self.lastseen = time.time()

    def add_command(self, command):
        """
        Adds a command (type: string) to the queue for the agent
        to execute.
        """
        self.command_queue.put(command)

    def add_task(self, task):
        """
        Adds a task (type: string) to the queue for the agent
        to execute.
        """
        self.task_queue.put(task)

    def get_task(self):
        """
        Gets the most recent task in the agent's
        task queue.
        """
        if self.task_queue.empty():
            return False
        else:
            return self.task_queue.get()

    def add_payload(self, payload_script):
        """
        Adds a payload (type: string) to the queue for the agent
        to execute.
        """
        self.payload_queue.put(payload_script)

    def get_command(self):
        """
        Gets the most recent command in the agent's
        command queue.
        """
        if self.command_queue.empty():
            return False
        else:
            return self.command_queue.get()

    def get_payload(self):
        """
        Gets the most recent payload in the agent's
        payload queue.
        """
        if self.payload_queue.empty():
            return False
        else:
            return self.payload_queue.get()
