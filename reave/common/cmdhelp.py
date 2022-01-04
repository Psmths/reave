from rich import print

doc = {
    "payload": {
        "list": ["list", "List all loaded payloads."],
        "info": [
            "info <payload name>",
            "List payload info of specified payload or current payload.",
        ],
        "use": ["use <payload name>", "Select payload to use."],
        "set": ["set <option> <value>", "Set payload option to specified value."],
        "run agent": [
            "run agent <agent uuid>",
            "Run the selected payload on the specified agent.",
        ],
        "run listener": [
            "run listener <listener uuid>",
            "Run the selected payload on all agents on the specified listener.",
        ],
    },
    "agent": {
        "list": ["list", "List all registered agents."],
        "info": ["info <uuid>", "List agent info, including any auto-enumerated data"],
        "interact": [
            "interact <uuid>",
            'Enter interactive command line. "quit" to exit',
        ],
        "create": ["create", "Start creating a new agent script."],
        "get": [
            "get <uuid> <file>",
            "Transfer file from the agent endpoint to downloads directory",
        ],
    },
    "listener": {
        "list": ["list", "List all active listeners."],
        "add": ["add <host> <port> <secret>", "Create and start a new listener."],
        "remove": ["remove <uuid>", "Remove specified listener."],
    },
}


def cmd_help(context, command):
    print(
        "[yellow]"
        + doc[context][command][0]
        + "\t"
        + doc[context][command][1]
        + "[/yellow]"
    )


def context_help(context):
    if context:
        for cmd, tooltip in doc[context].items():
            print(
                "[yellow][bold]"
                + tooltip[0]
                + "[/bold][italic]"
                + "\n\t"
                + tooltip[1]
                + "\n"
                + "[/italic][/yellow]"
            )
    else:
        print(
            "[yellow]Quickstart: https://github.com/Psmths/reave/blob/main/doc/commands.md\n[/yellow]"
        )
        print("[yellow]Available contexts:[/yellow]")
        for cmd in doc:
            print("[yellow]\t" + cmd + "[/yellow]")
