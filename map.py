import tcod as libtcod

from model.character import make_enemy
from model.item import Item
from model.object import Object

STAIRS_UP_NAME = 'stairs up'
STAIRS_DOWN_NAME = 'stairs down'


# map stuff
class Floor:
    def __init__(self, tiles, objects, rooms, dlevel=1):
        self.tiles = tiles
        self.objects = objects
        self.dungeon_level = dlevel
        self.rooms = rooms
        for o in objects:
            if o.name is STAIRS_DOWN_NAME:
                self.stairs_down = o
            elif o.name is STAIRS_UP_NAME:
                self.stairs_up = o

    def is_blocked(self, x, y):
        # first test the map tile
        if self.tiles[x][y].blocked:
            return True

        # now check for any blocking objects
        for o in self.objects:
            if o.blocks and o.x == x and o.y == y:
                return True

        return False

    def get_stuff(self, x, y):
        stuff = []
        for o in self.objects:
            if o.x == x and o.y == y:
                stuff.append(o)
        stuff.sort(key=lambda thing: thing.layer())
        return stuff


def cardinal_names(dx, dy):
    if dx < 0 and dy < 0:
        return "NW"
    if dx < 0 and dy == 0:
        return "W"
    if dx < 0 and dy > 0:
        return "SW"
    if dx == 0 and dy < 0:
        return "N"
    if dx == 0 and dy == 0:
        return "Here"
    if dx == 0 and dy > 0:
        return "S"
    if dx > 0 and dy < 0:
        return "NE"
    if dx > 0 and dy == 0:
        return "E"
    if dx > 0 and dy > 0:
        return "SE"
    raise Exception("Unknown direction")


class Tile:
    # a tile of the map and its properties
    def __init__(self, blocked, block_sight=None):
        self.explored = False
        self.blocked = blocked

        # by default, if a tile is blocked, it also blocks sight
        if block_sight is None: block_sight = blocked
        self.block_sight = block_sight


class Rect:
    # a rectangle on the map. used to characterize a room.
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h

    def center(self):
        center_x = int((self.x1 + self.x2) / 2)
        center_y = int((self.y1 + self.y2) / 2)
        return (center_x, center_y)

    def intersect(self, other):
        # returns true if this rectangle intersects with another one
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)


def create_room(tiles, room):
    # go through the tiles in the rectangle and make them passable
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            tiles[x][y].blocked = False
            tiles[x][y].block_sight = False


def create_h_tunnel(tiles, x1, x2, y):
    for x in range(min(x1, x2), max(x1, x2) + 1):
        tiles[x][y].blocked = False
        tiles[x][y].block_sight = False


def create_v_tunnel(tiles, y1, y2, x):
    # vertical tunnel
    for y in range(min(y1, y2), max(y1, y2) + 1):
        tiles[x][y].blocked = False
        tiles[x][y].block_sight = False


def from_dungeon_level(table, dungeon_level):
    # returns a value that depends on level. the table specifies what value occurs after each level, default is 0.
    for (value, level) in reversed(table):
        if dungeon_level >= level:
            return value
    return 0


def place_objects(room, dungeon_level):
    #     # this is where we decide the chance of each monster or item appearing.
    #
    #     # maximum number of monsters per room
    max_monsters = from_dungeon_level([[1, 1], [2, 4], [3, 6]], dungeon_level.dungeon_level)
    #
    #     # chance of each monster
    #     monster_chances = {'orc': 80, 'troll': from_dungeon_level([[15, 3], [30, 5], [60, 7]])}
    #
    #     # maximum number of items per room
    max_items = from_dungeon_level([[2, 1], [2, 4]], dungeon_level.dungeon_level)
    #
    #     # chance of each item (by default they have a chance of 0 at level 1, which then goes up)
    #     item_chances = {'heal': 35,
    #                     'lightning': from_dungeon_level([[25, 4]]),
    #                     'fireball': from_dungeon_level([[25, 6]]),
    #                     'confuse': from_dungeon_level([[10, 2]]),
    #                     'sword': from_dungeon_level([[5, 4]]),
    #                     'shield': from_dungeon_level([[15, 8]])}
    #
    #     # choose random number of monsters
    num_monsters = libtcod.random_get_int(None, 0, max_monsters)
    #
    for i in range(num_monsters):
        # choose random spot for this monster
        x = libtcod.random_get_int(0, room.x1 + 1, room.x2 - 1)
        y = libtcod.random_get_int(0, room.y1 + 1, room.y2 - 1)

        #         # only place it if the tile is not blocked
        if not dungeon_level.is_blocked(x, y):
            mook = make_enemy(x, y, dungeon_level)
            dungeon_level.objects.append(mook)

    #             choice = random_choice(monster_chances)
    #             if choice == 'orc':
    #                 # create an orc
    #                 fighter_component = Fighter(hp=20, defense=0, power=4, xp=35)
    #                 ai_component = BasicMonster()
    #
    #                 monster = Object(x, y, 'o', 'orc', libtcod.desaturated_green,
    #                                  blocks=True, fighter=fighter_component, ai=ai_component)
    #
    #             elif choice == 'troll':
    #                 # create a troll
    #                 fighter_component = Fighter(hp=30, defense=2, power=8, xp=100)
    #                 ai_component = BasicMonster()
    #
    #                 monster = Character(x, y, 'T', 'troll', libtcod.darker_green,
    #                                     blocks=True, fighter=fighter_component, ai=ai_component)
    #
    #             objects.append(monster)
    #
    #     # choose random number of items
    num_items = libtcod.random_get_int(None, 0, max_items)
    #
    for i in range(num_items):
        # choose random spot for this item
        x = libtcod.random_get_int(0, room.x1 + 1, room.x2 - 1)
        y = libtcod.random_get_int(0, room.y1 + 1, room.y2 - 1)
        #
        # only place it if the tile is not blocked
        if not dungeon_level.is_blocked(x, y):
            # choice = random_choice(item_chances)
            # if choice == 'heal':
            #     # create a healing potion
            item_component = Item()
            item_component.use_function = item_component.heal
            item = Object(x, y, '!', 'little a salami', libtcod.darker_crimson, item=item_component)
        #
        #             if choice == 'sword':
        #                 # create a sword
        #                 equipment_component = Equipment(slot='right hand', power_bonus=3)
        #                 item = Object(x, y, '/', 'sword', libtcod.sky, equipment=equipment_component)
        #
        #             elif choice == 'shield':
        #                 # create a shield
        #                 equipment_component = Equipment(slot='left hand', defense_bonus=1)
        #                 item = Object(x, y, '[', 'shield', libtcod.darker_orange, equipment=equipment_component)
        #
            dungeon_level.objects.append(item)
            # item.send_to_back()  # items appear below other objects
            item.always_visible = True  # items are visible even out-of-FOV, if in an explored area


# Map generation

def make_map(width, height, player):
    return make_map_rand_room(width, height, player)


def make_map_rand_room(width, height, player, max_rooms=30, min_room_size=6, max_room_size=10):
    # the list of objects starting with the player
    objects = [player]

    # fill map with "blocked" tiles
    map = [[Tile(True)
            for y in range(height)]
           for x in range(width)]

    rooms = []
    num_rooms = 0

    floor = Floor(map, objects, rooms)

    for r in range(max_rooms):
        # random width and height
        w = libtcod.random_get_int(0, min_room_size, max_room_size)
        h = libtcod.random_get_int(0, min_room_size, max_room_size)
        # random position without going out of the boundaries of the map
        x = libtcod.random_get_int(0, 0, width - w - 1)
        y = libtcod.random_get_int(0, 0, height - h - 1)

        # "Rect" class makes rectangles easier to work with
        new_room = Rect(x, y, w, h)

        # run through the other rooms and see if they intersect with this one
        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break

        if not failed:  # this room is valid

            # "paint" it to the map's tiles
            create_room(map, new_room)

            # add some contents to this room, such as monsters
            place_objects(new_room, floor)

            # center coordinates of new room, will be useful later
            (new_x, new_y) = new_room.center()

            if num_rooms == 0:
                # pass
                # this is the first room, where the player starts at
                player.x = new_x
                player.y = new_y
                up = Object(new_x, new_y, '<', STAIRS_UP_NAME, libtcod.white, always_visible=True)
                objects.append(up)
            else:
                # all rooms after the first:
                # connect it to the previous room with a tunnel

                # center coordinates of previous room
                (prev_x, prev_y) = rooms[num_rooms - 1].center()

                # draw a coin (random number that is either 0 or 1)
                if libtcod.random_get_int(0, 0, 1) == 1:
                    # first move horizontally, then vertically
                    create_h_tunnel(map, prev_x, new_x, prev_y)
                    create_v_tunnel(map, prev_y, new_y, new_x)
                else:
                    # first move vertically, then horizontally
                    create_v_tunnel(map, prev_y, new_y, prev_x)
                    create_h_tunnel(map, prev_x, new_x, new_y)

            # finally, append the new room to the list
            rooms.append(new_room)
            num_rooms += 1

    # create stairs at the center of the last room
    stairs = Object(new_x, new_y, '>', STAIRS_DOWN_NAME, libtcod.white, always_visible=True)
    objects.append(stairs)
    return Floor(map, objects, rooms)


def make_map_dir_cave(width, height, player, length, roughness, windiness, start_x=-1, start_y=2):
    pass


def make_map_test(width, height, player):
    # fill map with "blocked" tiles
    map = [[Tile(True)
            for y in range(height)]
           for x in range(width)]

    # create two rooms
    room1 = Rect(20, 15, 10, 15)
    room2 = Rect(50, 15, 10, 15)
    create_room(map, room1)
    create_room(map, room2)
    create_h_tunnel(map, 25, 55, 23)
    player.x = 23
    player.y = 25

    return Floor(map, [player], [room1, room2])
