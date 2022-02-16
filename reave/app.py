import os
import logging
import readline
import configparser
from sys import exit
from rich.console import Console
from common.payloads import Payloads
from common.menu import menu


def run():
    # Start the console
    console = Console()

    # Check if config file is present
    config = configparser.ConfigParser()
    config_file = os.path.join(os.path.dirname(__file__), "conf", "reave.conf")
    try:
        assert os.path.exists(config_file)
    except AssertionError:
        console.print(
            "[red]Configuration file not found! Did you run the installer?[/red]"
        )
        exit(0)

    # Read config parameters
    config.read(config_file)
    try:
        _LOGFILE = config["reave"]["logfile"]
        _CMD_HISTFILE = config["reave"]["histfile"]
        _CMD_HISTFILE_SIZE = int(config["reave"]["hist_size"])
    except KeyError:
        console.print("[red]Error reading the configuration[/red]")
        exit(0)
    except ValueError:
        console.print("[red]Error reading the configuration[/red]")
        exit(0)

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

    menu(agents, listeners, payloads).cmdloop()

    readline.set_history_length(_CMD_HISTFILE_SIZE)
    readline.write_history_file(_CMD_HISTFILE)
    
    logging.info("Shutting down...")


if __name__ == "__main__":
    run()
