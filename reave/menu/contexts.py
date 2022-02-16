def do_listener(self, cmd):
    """
    Switches the active context to listener
    """
    self.context = "listener"
    self.update_prompt()


def do_agent(self, cmd):
    """
    Switches the active context to agent
    """
    self.context = "agent"
    self.update_prompt()


def do_payload(self, cmd):
    """
    Switches the active context to payload
    """
    self.context = "payload"
    self.update_prompt()


def do_back(self, cmd):
    """
    Removes the currently active context
    """
    self.context = None
    self.update_prompt()
