class GameState:
    def __init__(self):
        self.clock = 0
        self.pending_moves = []  
        self.locked = set()      
        self.airborne = {}
        self.resting = {}
        self.resting_duration = {}