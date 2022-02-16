import os
import json
import time
import math
import threading
from rich.table import Table
from common.listener import Listener
from humanfriendly import format_size


def say(self, msg):
        if self.terminal_lock.acquire(blocking=False):
            self.async_alert(msg)
            self.terminal_lock.release()

def check_context(self, command_contexts):
    if self.context in command_contexts:
        return True
    print("Wrong context! This command must be run from the following context(s): " + ', '.join(command_contexts))
    return False

def emptyline(self):
    """
    This method prevents execution of the previous command when the user
    presses enter with a blank command in the prompt.
    """
    pass

def precmd(self, line):
    if self.interactive:
        if line.raw == "exit":
            self.interactive = False
            self.agent = None
            self.update_prompt()
            return ""
        else:
            self.agent.add_command(line.raw)
            return ""
    return line.raw

def update_prompt(self):
    """
    This method is called any time the user switches the context or the payload
    to update the prompt.
    """
    if self.payload:
        self.prompt = (
            self.context + "(" + self.payload.info["name"] + ") > "
            if self.context
            else "(" + self.payload.info["name"] + ") > "
        )
    elif self.interactive:
        self.prompt = (
            "(" + self.agent.uuid + ") > "
        )
    else:
        self.prompt = (self.context + " > ") if self.context else "> "

def last_seen_str(self, lastseen):
    """
    Method to convert agents lastseen time (UNIX format) to
    something more human-readable
    """
    current_time = time.time()
    delta = current_time - lastseen

    if delta < 1:
        return "CONNECTED"

    if delta < 60:
        return str(math.trunc(delta)) + " seconds ago"

    if 60 <= delta < 3600:
        return str(math.trunc(delta / 60)) + " minutes ago"

    if 3600 <= delta < 86400:
        return str(math.trunc(delta / 3600)) + " hours ago"

    if delta >= 86400:
        return str(math.trunc(delta / 86400)) + " days ago"

def list_listener(self):
    """
    Method to list all active listeners
    """
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("UUID")
    table.add_column("Listen Host")
    table.add_column("Listen Port")
    table.add_column("Association Key")
    for listener in self.listeners:
        table.add_row(
            str(listener.uuid), listener.host, str(listener.port), listener.secret
        )
    self.console.print(table)

def list_payload(self):
    """
    Method to list all loaded payloads
    """
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name")
    table.add_column("Description")
    for payload_name, payload in self.payloads.loaded_payloads.items():
        table.add_row(payload_name, payload.info["description"])
    self.console.print(table)

def list_agent(self):
    """
    Method to list all agents that have connected at least once to a listener
    """
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("UUID")
    table.add_column("Last Observed")
    table.add_column("Platform")
    table.add_column("Hostname")
    for uuid, agent in self.agents.items():
        a_status = "[green]" + self.last_seen_str(agent.lastseen) + "[/green]"
        if agent.beacon_expired():
            a_status = "[red](!) " + self.last_seen_str(agent.lastseen) + "[/red]"
        table.add_row(uuid, a_status, agent.get_platform(), agent.get_hostname())
    self.console.print(table)

def agent_info(self, agent):
        """
        Method to display all auto-enumerated agent information
        """
        if self.stdout_format == "table":
            table = Table(
                show_header=True, header_style="bold magenta", title="Agent Options"
            )
            table.add_column("Option")
            table.add_column("Value")
            for key, value in json.loads(agent.enumdata["agent_options"]).items():
                if key in ["TRANSFER_BLOCK_SIZE"]:
                    table.add_row(key, format_size(int(value)))
                else:
                    table.add_row(key, str(value))
            self.console.print(table)

            if "host_local_users" in agent.enumdata["host_data"]:
                table = Table(
                    show_header=True, header_style="bold magenta", title="Local Users"
                )
                table.add_column("Username")
                table.add_column("User Description")
                host_local_users = agent.enumdata["host_data"]["host_local_users"]
                for uname, user in host_local_users.items():
                    table.add_row(uname, user["description"])
                self.console.print(table)

            if "host_mounts" in agent.enumdata["host_data"]:
                table = Table(
                    show_header=True, header_style="bold magenta", title="Mountpoints"
                )
                table.add_column("UUID")
                table.add_column("Mountpoint")
                table.add_column("Name")
                table.add_column("Type")
                table.add_column("Size")
                table.add_column("Free")

                mounts = agent.enumdata["host_data"]["host_mounts"]

                for uuid, mount in mounts.items():
                    table.add_row(
                        uuid,
                        mount["mountpoint"],
                        mount["name"],
                        mount["type"],
                        format_size(int(mount["size"])),
                        format_size(int(mount["free"])),
                    )
                self.console.print(table)

        if self.stdout_format == "json":
            print(agent.enumdata)

def add_listener(self, host, port, secret):
    """
    Method used to add a new listener
    """
    try:
        assert os.path.exists("reave/data/cert.pem")
    except AssertionError:
        print(
            "Couldnt locate certificate file! Did you run the installer?"
        )
        return
    l = Listener(port, host, secret, self)
    threading.Thread(target=l.main_thread).start()
    self.listeners.append(l)

def remove_listener(self, listener_uuid):
    """
    Method to destroy a listener
    """
    selected_listener = (
        _[0]
        if (
            _ := [
                listener
                for listener in self.listeners
                if listener.uuid == listener_uuid
            ]
        )
        else None
    )

    if selected_listener:
        # Stop selected listener
        selected_listener.close()
        # Remove listener from list
        self.listeners = list(
            filter(lambda listener: listener.uuid != listener_uuid, self.listeners)
        )
    else:
        print("Listener not found!")

def close_listeners(self):
    """
    Method to stop all active listeners for a graceful
    shutdown
    """
    if self.listeners:
        print(
            "Executing graceful shutdown of all active listeners..."
        )
        for listener in self.listeners:
            print(str(listener.uuid) + " - Listener shutting down")
            listener.close()