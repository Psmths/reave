import os
import imp
import logging
from pathlib import Path
from rich.console import Console
from rich.table import Table


class Payloads:
    """
    Handle loading and configuration of payloads
    """

    def __init__(self):
        self.loaded_payloads = {}
        self.logger = logging.getLogger(__name__)

    def load_payloads(self):
        """
        Load all payloads in the payload directory
        """
        logging.info("Loading payloads")
        payload_path = "reave/payloads"
        for root, dirs, files in os.walk(payload_path):
            for file in files:
                if file.endswith(".py"):
                    logging.debug("Found payload file: " + file)
                    payload_name = file
                    self.loaded_payloads[payload_name] = imp.load_source(
                        payload_name, root + "/" + file
                    ).Payload()
        logging.info("Loaded %s payload scripts!", str(len(self.loaded_payloads)))

    def get_payload_by_name(self, payload_name):
        """
        Return payload object from its name
        """
        try:
            return self.loaded_payloads[payload_name]
        except KeyError:
            return False

    def print_payloads_info(self, p):
        """
        Print payload information
        """
        console = Console()

        table = Table(show_header=False, header_style="bold magenta")
        table.add_column()
        table.add_column()
        table.add_row("Name", p.info["name"])
        table.add_row("Description", p.info["description"])
        table.add_row("Author", p.info["author"])
        table.add_row("Date", p.info["date"])
        table.add_row("Compatibility", p.info["compatibility"])
        console.print(table)

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Setting")
        table.add_column("Value")
        table.add_column("Description")
        for key, value in p.options.items():
            table.add_row(key, str(value["value"]), value["info"])
        console.print(table)
