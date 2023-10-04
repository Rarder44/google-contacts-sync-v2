class SynchronizationLists:
    def __init__(self) -> None:
        self.toAdd=[]
        self.toRemove=[]
        self.toUpdate=[]
    

    @property
    def countAll(self):
        return len(self.toAdd)+len(self.toRemove)+len(self.toUpdate)
        