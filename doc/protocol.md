# Protocol Structure

The command and control protocol is ASCII-only and has three distinct packet types:

 - `_associate`
 - `_beacon`
 - `_response`

The protocol leverages TCP for transmission.

## Association Packet

The `_associate` packet is used at the start of a new agent onboarding. It will provide the listener with the agent's secret phrase, and the agent's UUID. If the agent has sent the correct secret phrase to the listener, the listener instance will register the agent, which can then proceed to beaconing. The association packet looks like this:

```
_associate{"secret": "mysecret", "uuid": "f3c71828f0b542d6d58030f089fdfdc7"}
```


The expected response to a successful association process is a status OK response packet, which looks like:

```
_response{"status" : "ACK"}
```

## Beacon Packet

The `_beacon` packet is used by an agent to periodically pull information from its listener. Upon receipt of this packet type, the listener will see if there are commands or payloads for the agent and send them, with commands taking precedence over payloads. Commands and payloads are send as part of the response JSON and are encoded with base85. An example beacon packet:

```
_beacon{"secret": "mysecret", "uuid": "f3c71828f0b542d6d58030f089fdfdc7"}
```

The expected response to a beacon packet looks like so:

No command or payload:
```
_response{"status": "OK", "command": null, "payload": null}
```

Command:
```
_response{"status": "OK", "command": F`(W)AKWR5, "payload": null}
```

## Response Packets


`_response` packets are used for general responses, bidirectionally. For instance, when the agent has executed a command and has output data for the listener, it will send a packet like this:

```
_response{"status": "OK", "d": F`(W)AKWR5, "payload": null}
```

## Example Flow

```
Agent       -> Listener     _associate{"secret": "mysecret", "uuid": "f3c71828f0b542d6d58030f089fdfdc7"}
Listener    -> Agent        _response{"status" : "ACK"}
Agent       -> Listener     _beacon{"secret": "mysecret", "uuid": "f3c71828f0b542d6d58030f089fdfdc7"}
Listener    -> Agent        _response{"status": "OK", "command": F`(W)AKWR5, "payload": null}
Agent       -> Listener     _response{"status": "OK", "data": 9PJBeGT^O.@PBMZ2(gU;/hek;/R`L,2D...}
```

## Encryption

All communications between agents and listeners are passed through a TLS socket. The certificate used for the socket is generated as a part of the initial installation procedure.