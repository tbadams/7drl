class Message:
    def __init__(self, text, color):
        self.text = text
        self.color = color

    def as_args(self):
        return self.text, self.color
