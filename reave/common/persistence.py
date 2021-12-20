import tinydb


class Persistence:
    """
    Persistence class is responsible for saving and restoring:

      - Listener Table
      - Agent Table
    """

    def __init__(self, listener_table, agent_table):
        self.listener = listener
