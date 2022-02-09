import os
import logging
import readline
import threading
from sys import exit
from rich import print
from rich.console import Console
from common.payloads import Payloads
from common.mainmenu import MainMenu

# TODO: Parse configfile for cmd history and log settings
_LOGFILE = ".reave_log"
_CMD_HISTFILE = ".reave_history"
_CMD_HISTFILE_SIZE = 1000


def app_close():
    readline.set_history_length(_CMD_HISTFILE_SIZE)
    readline.write_history_file(_CMD_HISTFILE)
    logging.info("Shutting down...")
    exit(0)


if __name__ == "__main__":
    # TODO: Add log rotation
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

    MainMenu(agents, listeners, payloads).cmdloop_ki()
    app_close()
