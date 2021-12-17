# Command Line Interface

The command line has three distinct contexts:

 - Listener
 - Payload
 - Agent

## Listener Context Commands

To enter the listener context, use command `listener`. From there, several options are available:

```
list                            List all active listeners
add <host> <port> <secret>      Add a listener
remove <uuid>                   Remove a listener
```

Exit this context by using command `back`

## Agent Context Commands

To enter the agent context, use command `agent`. From there, several options are available:

```
list                    List all agents
interact <uuid>         Interactive terminal session with agent. 
                        'quit' to exit.
create                  Start creating a new agent script.
                        Will write to ./data/ directory
```

Exit this context by using command `back`

## Payload Context Commands

To enter the `payload` context, use command `payload`. From there, several options are available:

```
list                    List all loaded payloads
info <name>             Get information about a payload
use <name>              Select payload for use
set <option> <value>    Set payload option to value
run agent <uuid>        Run the payload on an individual agent
run listener <uuid>     Run the payload on all agents on the listener
```

Exit this context by using command `back`