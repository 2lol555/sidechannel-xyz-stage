class AutomaticAlignmentCannotBePerformed(Exception):

    def __init__(self, message):
        self.add_note(message)
