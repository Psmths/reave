import os
import cmd
import sys
import json
import math
import time
import readline
import threading
from rich import print
from rich.console import Console
from rich.table import Table
from common.listener import Listener
from common.cmdhelp import cmd_help, context_help


class MainMenu(cmd.Cmd):
    """
    MainMenu class is responsible for user interface
    """

    def __init__(self, agents, listeners, payloads):

        cmd.Cmd.__init__(self)
        readline.set_completer_delims(" ")

        self.agents = agents  # Dictionary of agents
        self.listeners = listeners  # List of listeners
        self.payloads = payloads  # Object containing all payloads
        self.console = Console()  # Console for stdout
        self.context = None  # Current context
        self.payload = None  # Current payload
        self.agent = None  # Current agent
        self.prompt = "> "  # Prompt for command line interfact
        self.stdout_format = "table"  # Formatting option for data output
        self.active = True  # Bool to exit cmdloop gracefully

    def complete_interact(self, text, line, begidx, endidx):
        """
        Offer available agents that the user can interact with
        """
        if self.context == "agent":
            return [i for i, a in self.agents.items() if i.startswith(text)]

    def complete_info(self, text, line, begidx, endidx):
        """
        Offer available agents that the user can get information from
        """
        if self.context == "agent":
            return [i for i, a in self.agents.items() if i.startswith(text)]

    def complete_get(self, text, line, begidx, endidx):
        """
        Offer available agents that the user can get files from
        """
        if self.context == "agent":
            return [i for i, a in self.agents.items() if i.startswith(text)]

    def complete_remove(self, text, line, begidx, endidx):
        """
        Offer available listeners that the user can remove
        """
        if self.context == "listener":
            return [i.uuid for i in self.listeners if i.uuid.startswith(text)]

    def complete_use(self, text, line, begidx, endidx):
        """
        Offer available payloads that the user can select
        """
        if self.context == "payload":
            return [i for i in self.payloads.loaded_payloads if i.startswith(text)]

    def do_help(self, cmd):
        """
        Offer help to the user. If the context is None, return general information.
        If the context is active (agent,listener,payload), return all available
        commands for that context.
        """
        if self.context:
            context_help(self.context.split(" ")[0])
        else:
            context_help(None)

    def emptyline(self):
        """
        This method prevents execution of the previous command when the user
        presses enter with a blank command in the prompt.
        """
        pass

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
        else:
            self.prompt = (self.context + " > ") if self.context else "> "

    def do_listener(self, cmd):
        """
        Switches the active context to listener
        """
        self.context = "listener"
        self.update_prompt()

    def do_agent(self, cmd):
        """
        Switches the active context to agent
        """
        self.context = "agent"
        self.update_prompt()

    def do_payload(self, cmd):
        """
        Switches the active context to payload
        """
        self.context = "payload"
        self.update_prompt()

    def do_back(self, cmd):
        """
        Removes the currently active context
        """
        self.context = None
        self.update_prompt()

    def do_format(self, cmd):
        """
        Method to switch the formatting of returned data. Currently
        this only impacts auto-enumerated data for connected agents.
        """
        try:
            assert len(cmd.split()) == 1
        except AssertionError:
            context_help("format")
            return
        cmd = cmd.split()
        requested_format = cmd[0]
        try:
            assert requested_format in ["json", "table"]
        except AssertionError:
            context_help("format")
            return
        self.stdout_format = requested_format

    def do_add(self, cmd):
        """
        Method to add a new listener
        """
        try:
            assert self.context == "listener"
        except AssertionError:
            print("wrong context")
            return
        try:
            assert len(cmd.split()) == 3
        except AssertionError:
            cmd_help("listener", "add")
            return
        cmd = cmd.split()
        host = cmd[0]
        port = cmd[1]
        secret = cmd[2]
        try:
            # TODO: Check port before a listener is attempted
            port = int(port)
        except ValueError:
            cmd_help("listener", "add")
            return
        self.add_listener(host, port, secret)

    def do_remove(self, cmd):
        """
        Method to remove an active listener
        """
        try:
            assert self.context == "listener"
        except AssertionError:
            print("wrong context")
            return
        try:
            assert len(cmd.split()) == 1
        except AssertionError:
            cmd_help("listener", "remove")
            return
        cmd = cmd.split()
        listener_uuid = cmd[0]
        self.remove_listener(listener_uuid)

    def do_list(self, cmd):
        """
        Method to list agents, listeners, and payloads
        """

        if self.context is None:
            print("No context specified")
            return

        if self.context == "listener":
            self.list_listener()
        if self.context == "payload":
            self.list_payload()
        if self.context == "agent":
            self.list_agent()

    def do_ls(self, cmd):
        """
        Alias for the list command
        """
        self.do_list(cmd)

    def do_interact(self, cmd):
        """
        Method to spawn an interactive terminal session
        with a connected agent
        """
        try:
            assert self.context == "agent"
        except AssertionError:
            print("wrong context")
            return
        try:
            assert len(cmd.split()) == 1
        except AssertionError:
            cmd_help("agent", "interact")
            return
        cmd = cmd.split()
        uuid = cmd[0]
        try:
            assert uuid in self.agents
        except AssertionError:
            print("Agent not found!")
            return

        print("Entering interactive session. Type quit to end session.")
        while True:
            interactive_cmd = input(uuid[0:7] + " > ")
            if interactive_cmd == "quit":
                break
            # Add the requested command to the agent's command queue
            self.agents[uuid].add_command(interactive_cmd)

    def do_get(self, cmd):
        """
        Method to request a file transfer from an agent to the
        server
        """
        try:
            assert self.context == "agent"
        except AssertionError:
            print("wrong context")
            return
        try:
            assert len(cmd.split()) == 2
        except AssertionError:
            cmd_help("agent", "get")
            return
        cmd = cmd.split()
        uuid = cmd[0]
        file = cmd[1]
        try:
            assert uuid in self.agents
        except AssertionError:
            print("Agent not found!")
            return

        get_task = {
            "cmd": "GET_FILE",
            "file": file,
        }
        self.agents[uuid].add_task(json.dumps(get_task))

    def do_use(self, cmd):
        """
        Method to select a payload
        """
        try:
            assert self.context == "payload"
        except AssertionError:
            print("wrong context")
            return
        try:
            assert len(cmd.split()) == 1
        except AssertionError:
            cmd_help("payload", "use")
            return
        cmd = cmd.split()
        payload_name = cmd[0]
        self.payload = self.payloads.get_payload_by_name(payload_name)
        if self.payload:
            self.update_prompt()
        else:
            self.payload = None
            print("Payload not found!")

    def do_info(self, cmd):
        """
        Method to display information about a loaded payload or
        display enumerated data from an agent
        """
        try:
            assert self.context in ["payload", "agent"]
        except AssertionError:
            print("wrong context")
            return
        if self.context == "payload":
            if not self.payload:
                try:
                    assert len(cmd.split()) == 1
                except AssertionError:
                    cmd_help("payload", "info")
                    return
                cmd = cmd.split()
                p = self.payloads.get_payload_by_name(cmd[0])
                if p:
                    self.payloads.print_payloads_info(p)
                else:
                    print("Payload not found!")
            else:
                self.payloads.print_payloads_info(self.payload)
        if self.context == "agent":
            try:
                assert len(cmd.split()) == 1
            except AssertionError:
                cmd_help("agent", "info")
                return
            cmd = cmd.split()
            uuid = cmd[0]
            try:
                assert uuid in self.agents
            except AssertionError:
                print("Agent not found!")
                return
            self.agent_info(self.agents[uuid])

    def do_set(self, cmd):
        """
        Method that allows the user to modify payload settings
        """
        try:
            assert self.context == "payload"
        except AssertionError:
            print("wrong context")
            return
        try:
            assert self.payload is not None
        except AssertionError:
            print("No payload selected!")
            return
        try:
            assert len(cmd.split()) >= 2
        except AssertionError:
            cmd_help("payload", "set")
            return
        cmd = cmd.split()
        option = cmd[0]
        value = " ".join(cmd[1:])
        try:
            assert option in self.payload.options
        except AssertionError:
            print("Invalid option selected!")
            return

        # Translate between use input and special python types
        if value in ["False", "false", "0", 0]:
            self.payload.options[option]["value"] = False
        elif value in ["True", "true", "1", 1]:
            self.payload.options[option]["value"] = True
        elif value in ["None", "none"]:
            self.payload.options[option]["value"] = None
        else:
            self.payload.options[option]["value"] = value

    def do_run(self, cmd):
        """
        Method to deploy a payload to a selected agent
        """
        try:
            assert self.context == "payload"
        except AssertionError:
            print("wrong context")
            return
        try:
            assert self.payload is not None
        except AssertionError:
            print("No payload selected!")
            return
        try:
            assert len(cmd.split()) == 2
        except AssertionError:
            cmd_help("payload", "run agent")
            # TODO: implement listener-level payload run
            # cmd_help('payload', 'run listener')
            return
        cmd = cmd.split()
        script = self.payload.gen_payload()
        if cmd[0] == "agent":
            uuid = cmd[1]
            try:
                assert uuid in self.agents
            except AssertionError:
                print("Agent not found!")
                return
            self.agents[uuid].add_payload(script)

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
                        mount["size"],
                        mount["free"],
                    )
                self.console.print(table)

        if self.stdout_format == "json":
            self.console.print(agent.enumdata)

    def add_listener(self, host, port, secret):
        """
        Method used to add a new listener
        """
        try:
            assert os.path.exists("reave/data/cert.pem")
        except AssertionError:
            print(
                "[red]Couldnt locate certificate file! Did you run the installer?[/red]"
            )
            return
        l = Listener(port, host, secret, self.agents, self.listeners)
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
            self.console.print("[red]Listener not found![/red]")

    def close_listeners(self):
        """
        Method to stop all active listeners for a graceful
        shutdown
        """
        if self.listeners:
            self.console.print(
                "[blue]Executing graceful shutdown of all active listeners...[/blue]"
            )
            for listener in self.listeners:
                print(
                    "[blue]" + str(listener.uuid) + " - Listener shutting down[/blue]"
                )
                listener.close()

    def do_EOF(self, line):
        """
        Handle EOF
        """
        return True

    def do_quit(self, cmd):
        """
        Method to exit reave
        """
        self.close_listeners()
        sys.stdout.write("\n")
        self.active = False
        return True

    def cmdloop_ki(self):
        """
        Main cmdloop that catches KeyboardInterrupt and
        shuts down reave gracefully
        """
        while self.active:
            try:
                self.cmdloop()
            except KeyboardInterrupt:
                self.close_listeners()
                sys.stdout.write("\n")
                return
