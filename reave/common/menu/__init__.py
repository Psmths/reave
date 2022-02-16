from cmd2 import Cmd
import readline
from rich.console import Console


class menu(Cmd):
    """
    MainMenu class is responsible for user interface
    """

    # Completion functions
    from common.menu.completion import complete_interact
    from common.menu.completion import complete_info
    from common.menu.completion import complete_get
    from common.menu.completion import complete_remove
    from common.menu.completion import complete_use

    # Helper methods
    from common.menu.helpers import say
    from common.menu.helpers import check_context
    from common.menu.helpers import emptyline
    from common.menu.helpers import update_prompt
    from common.menu.helpers import precmd
    from common.menu.helpers import last_seen_str
    from common.menu.helpers import list_agent
    from common.menu.helpers import list_listener
    from common.menu.helpers import list_payload
    from common.menu.helpers import agent_info
    from common.menu.helpers import add_listener
    from common.menu.helpers import remove_listener
    from common.menu.helpers import close_listeners

    # Context commands
    from common.menu.contexts import do_listener
    from common.menu.contexts import do_agent
    from common.menu.contexts import do_payload
    from common.menu.contexts import do_back

    # Available commands
    from common.menu.commands import do_help
    from common.menu.commands import do_format
    from common.menu.commands import do_add
    from common.menu.commands import do_remove
    from common.menu.commands import do_list
    from common.menu.commands import do_ls
    from common.menu.commands import do_interact
    from common.menu.commands import do_exfil
    from common.menu.commands import do_get
    from common.menu.commands import do_use
    from common.menu.commands import do_info
    from common.menu.commands import do_set
    from common.menu.commands import do_run
    from common.menu.commands import do_EOF
    from common.menu.commands import do_quit

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