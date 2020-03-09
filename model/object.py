from enum import auto, IntEnum

import tcod as libtcod

from model.item import Item


class Object:
    # this is a generic object: the player, a monster, an item, the stairs...
    # it's always represented by a character on screen.
    def __init__(self, x, y, char, name, color, blocks=False, item=None, equipment=None, always_visible=False, fighter=None):
        self.name = name
        self.blocks = blocks
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.item = item
        self.always_visible = always_visible
        self.fighter = fighter
        self.ai = None
        if self.item:  # let the Item component know who owns it
            self.item.owner = self

        self.equipment = equipment
        if self.equipment:  # let the Equipment component know who owns it
            self.equipment.owner = self

            # there must be an Item component for the Equipment component to work properly
            self.item = Item()
            self.item.owner = self
            
    def __str__(self):
        return str(self.name)

    # def move(self, dx, dy, player, message, objects, is_blocked):
    #     # move by the given amount if not blocked
    #     if not is_blocked(self.x + dx, self.y + dy, objects):
    #         self.x += dx
    #         self.y += dy
    #     elif self is player:
    #         message("Ouch! You blunder into a wall.", libtcod.orange)
    #         player.fighter.take_damage(random.randint(1, 10), "running into a wall")

    def draw(self, con, fov_map):
        if libtcod.map_is_in_fov(fov_map, self.x, self.y):
            # set the color and then draw the character that represents this object at its position
            libtcod.console_set_default_foreground(con, self.color)
            libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)

    def clear(self, con):
        # erase the character that represents this object
        libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)

    def layer(self):
        if self.fighter:
            return Layer.CHARACTER
        if self.item:
            return Layer.ITEM
        return Layer.TRASH


class Layer(IntEnum):
    TILE = auto()
    TRASH = auto()
    ITEM = auto()
    CHARACTER = auto()
