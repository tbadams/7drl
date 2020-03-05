class Item:
    # an item that can be picked up and used.
    def __init__(self, use_function=None):
        self.use_function = use_function
        self.owner = None