from cmd2 import Cmd
import readline
from rich.console import Console


class menu(Cmd):
    """
    MainMenu class is responsible for user interface
    """

    # Completion functions
    from menu.completion import complete_interact
    from menu.completion import complete_info
    from menu.completion import complete_get
    from menu.completion import complete_remove
    from menu.completion import complete_use

    # Helper methods
    from menu.helpers import say
    from menu.helpers import check_context
    from menu.helpers import emptyline
    from menu.helpers import update_prompt
    from menu.helpers import precmd
    from menu.helpers import last_seen_str
    from menu.helpers import list_agent
    from menu.helpers import list_listener
    from menu.helpers import list_payload
    from menu.helpers import agent_info
    from menu.helpers import add_listener
    from menu.helpers import remove_listener
    from menu.helpers import close_listeners

    # Context commands
    from menu.contexts import do_listener
    from menu.contexts import do_agent
    from menu.contexts import do_payload
    from menu.contexts import do_back

    # Available commands
    from menu.commands import do_help
    from menu.commands import do_format
    from menu.commands import do_add
    from menu.commands import do_remove
    from menu.commands import do_list
    from menu.commands import do_ls
    from menu.commands import do_interact
    from menu.commands import do_exfil
    from menu.commands import do_get
    from menu.commands import do_use
    from menu.commands import do_info
    from menu.commands import do_set
    from menu.commands import do_run
    from menu.commands import do_EOF
    from menu.commands import do_quit

    def __init__(self, agents, listeners, payloads):

        Cmd.__init__(self)
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
        self.interactive = False

    def sigint_handler(self, signum: int, frame) -> None:
        if signum == 2:
            self.do_quit("ki")
