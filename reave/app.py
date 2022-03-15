import os
import logging
import readline
import configparser
from sys import exit
from rich.console import Console
from payloads import Payloads
from menu import menu
from logging.handlers import RotatingFileHandler


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
        _LOGFILE_MAX_SIZE_BYTES = int(config["reave"]["logfile_max_bytes"])
        _CMD_HISTFILE = config["reave"]["histfile"]
        _CMD_HISTFILE_SIZE = int(config["reave"]["hist_size"])

    except KeyError:
        console.print("[red]Error reading the configuration[/red]")
        exit(0)
    except ValueError:
        console.print("[red]Error reading the configuration[/red]")
        exit(0)

    handler = RotatingFileHandler(
        _LOGFILE, maxBytes=_LOGFILE_MAX_SIZE_BYTES, backupCount=1
    )
    logger = logging.getLogger()
    logging.basicConfig(
        filename=_LOGFILE,
        filemode="a",
        format="%(asctime)s [%(levelname)s] [%(module)s] %(message)s",
    )
    logger.setLevel(logging.DEBUG)
    # logger.addHandler(handler)

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
