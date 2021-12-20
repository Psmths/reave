import os
import imp
import logging
from rich import print
from pathlib import Path
from rich.console import Console
from rich.table import Column, Table


class Payloads:
    def __init__(self):
        self.loaded_payloads = {}
        self.logger = logging.getLogger(__name__)
    
    def load_payloads(self):
        logging.info('Loading payloads')
        root_path = self.get_root()
        payload_path = root_path/'reave'/'payloads'
        for root, dirs, files in os.walk(payload_path):
            for file in files:
                if file.endswith(".py"):
                    logging.debug('Found payload file: ' + file)
                    payload_name = file
                    self.loaded_payloads[payload_name] = imp.load_source(payload_name,root+'/'+file).Payload()
        logging.info('Loaded ' + str(len(self.loaded_payloads)) + ' payload scripts!')

    def get_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    def get_payload_by_name(self, payload_name):
        try:
            return self.loaded_payloads[payload_name]
        except KeyError:
            return False

    def print_payloads_info(self, p):
        console = Console()
        
        table = Table(show_header=False, header_style="bold magenta")
        table.add_column()
        table.add_column()
        table.add_row("Name", p.info['name'])
        table.add_row("Description", p.info['description'])
        table.add_row("Author", p.info['author'])
        table.add_row("Date", p.info['date'])
        table.add_row("Compatibility", p.info['compatibility'])
        console.print(table)

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Setting")
        table.add_column("Value")
        table.add_column("Description")
        for key, value in p.options.items():
            table.add_row(
                key,
                str(value['value']),
                value['info']
            )
        console.print(table)
