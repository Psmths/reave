def complete_interact(self, text, line, begidx, endidx):
    """
    Offer available agents that the user can interact with
    """
    if self.context == "agent":
        return [i for i, a in self.agents.items() if i.startswith(text)]
    return []


def complete_info(self, text, line, begidx, endidx):
    """
    Offer available agents that the user can get information from
    """
    if self.context == "agent":
        return [i for i, a in self.agents.items() if i.startswith(text)]
    return []


def complete_get(self, text, line, begidx, endidx):
    """
    Offer available agents that the user can get files from
    """
    if self.context == "agent":
        return [i for i, a in self.agents.items() if i.startswith(text)]
    return []


def complete_remove(self, text, line, begidx, endidx):
    """
    Offer available listeners that the user can remove
    """
    if self.context == "listener":
        return [i.uuid for i in self.listeners if i.uuid.startswith(text)]
    return []


def complete_use(self, text, line, begidx, endidx):
    """
    Offer available payloads that the user can select
    """
    if self.context == "payload":
        return [i for i in self.payloads.loaded_payloads if i.startswith(text)]
    return []
