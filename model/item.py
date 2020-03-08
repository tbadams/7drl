from msg import Message
import tcod as libtcod


class Item:
    # an item that can be picked up and used.
    def __init__(self, use_function=None, owner=None):
        self.use_function = use_function
        self.owner = owner

    def heal(self, user, amount=10):
        user.fighter.heal(amount)
        return [Message("You have " + self.owner.name + ", as a treat.", libtcod.green)]
