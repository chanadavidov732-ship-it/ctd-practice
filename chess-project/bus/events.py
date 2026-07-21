from dataclasses import dataclass


@dataclass
class ClientConnected:
    client_id: str
