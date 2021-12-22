import os
import logging
import readline
import threading
from sys import exit
from rich import print
from rich.console import Console
from signal import signal, SIGINT
from common.payloads import Payloads
from common.mainmenu import MainMenu

_LOGFILE = ".reave_log"
_CMD_HISTFILE = ".reave_history"
_CMD_HISTFILE_SIZE = 1000
_keyboard_interrupt = threading.Event()


def handler(signal_received, frame):
    print(
        "[bold][red]Please wait for gracefule shutdown of active listeners...[/red][/bold]"
    )
    logging.info("Shutting down all listeners...")
    _keyboard_interrupt.set()
    readline.set_history_length(_CMD_HISTFILE_SIZE)
    readline.write_history_file(_CMD_HISTFILE)
    logging.info("Shutting down...")
    exit(0)


if __name__ == "__main__":

    logging.basicConfig(
        filename=_LOGFILE,
        filemode="a",
        format="%(asctime)s [%(levelname)s] [%(module)s] %(message)s",
    )
    logging.getLogger().setLevel(logging.DEBUG)

    agents = {}
    listeners = []
    payloads = Payloads()

    logging.info("Starting REAVE...")

    payloads.load_payloads()

    signal(SIGINT, handler)

    if os.path.exists(_CMD_HISTFILE):
        readline.read_history_file(_CMD_HISTFILE)

    console = Console()

    console.print(
        """[yellow]
    ██████╗ ███████╗ █████╗ ██╗   ██╗███████╗
    ██╔══██╗██╔════╝██╔══██╗██║   ██║██╔════╝
    ██████╔╝█████╗  ███████║██║   ██║█████╗  
    ██╔══██╗██╔══╝  ██╔══██║╚██╗ ██╔╝██╔══╝  
    ██║  ██║███████╗██║  ██║ ╚████╔╝ ███████╗
    ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝
    ~ Hypervisor Post-Exploit Framework ~
        [/yellow]"""
    )

    MainMenu(agents, listeners, payloads, _keyboard_interrupt).cmdloop()
