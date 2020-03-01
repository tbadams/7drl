import tcod as libtcod
import textwrap
import math
import random

# actual size of the window
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 52

MSG_X = 2
MSG_WIDTH = SCREEN_WIDTH - 4
MSG_HEIGHT = 5

# map size
MAP_WIDTH = 80
MAP_HEIGHT = 43
MAP_Y = MSG_HEIGHT

# GUI
PANEL_HEIGHT = 4
BAR_WIDTH = 20
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT

INVENTORY_WIDTH = 50
CHARACTER_SCREEN_WIDTH = 30
LEVEL_SCREEN_WIDTH = 40

# fov
FOV_ALGO = 0  # default FOV algorithm
FOV_LIGHT_WALLS = True
MAX_LIGHT_RADIUS = 10

LIMIT_FPS = 20  # 20 frames-per-second maximum

# game state strings
STRING_EXIT = 'exit'
STRING_NO_ACTION = 'didnt-take-turn'
STRING_PLAYING = 'playing'

# experience and level-ups
LEVEL_UP_BASE = 200
LEVEL_UP_FACTOR = 150

# colors
color_dark_wall = libtcod.Color(0, 0, 100)
color_dark_ground = libtcod.Color(50, 50, 150)
color_light_wall = libtcod.Color(130, 110, 50)
color_light_ground = libtcod.Color(200, 180, 50)

WALL_DMG = 10

# game state
game_msgs = []
inventory = []
dungeon_level = 1
stairs = None


# player, inventory


class Object:
    # this is a generic object: the player, a monster, an item, the stairs...
    # it's always represented by a character on screen.
    def __init__(self, x, y, char, name, color, blocks=False, item=None, equipment=None):
        self.name = name
        self.blocks = blocks
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.item = item
        if self.item:  # let the Item component know who owns it
            self.item.owner = self

        self.equipment = equipment
        if self.equipment:  # let the Equipment component know who owns it
            self.equipment.owner = self

            # there must be an Item component for the Equipment component to work properly
            self.item = Item()
            self.item.owner = self

    def move(self, dx, dy):
        # move by the given amount if not blocked
        if not is_blocked(self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy
        elif self is player:
            message("Ouch! You blunder into a wall.", libtcod.orange)
            player.fighter.take_damage(random.randint(1, WALL_DMG))

    def draw(self):
        if libtcod.map_is_in_fov(fov_map, self.x, self.y):
            # set the color and then draw the character that represents this object at its position
            libtcod.console_set_default_foreground(con, self.color)
            libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)

    def clear(self):
        # erase the character that represents this object
        libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)


class Character(Object):
    def __init__(self, x, y, char, name, color, blocks=False, fighter=None):
        super().__init__(x, y, char, name, color, blocks)
        self.fighter = fighter
        if self.fighter:
            fighter.owner = self

        self.level = 1

    def get_all_equipped(self):  # returns a list of equipped items
        if self == player:
            equipped_list = []
            for item in inventory:
                if item.equipment and item.equipment.is_equipped:
                    equipped_list.append(item.equipment)
            return equipped_list
        else:
            return []  # other objects have no equipment

    def get_equipped_in_slot(self, slot):  # returns the equipment in a slot, or None if it's empty
        for obj in inventory:
            if obj.equipment and obj.equipment.slot == slot and obj.equipment.is_equipped:
                return obj.equipment
        return None


class Fighter:
    # combat-related properties and methods (monster, player, NPC).
    def __init__(self, hp, defense, power, xp, death_function=None, owner=None):
        self.base_max_hp = hp
        self.hp = hp
        self.base_defense = defense
        self.base_power = power
        self.xp = xp
        self.death_function = death_function
        self.owner = owner

    @property
    def power(self):  # return actual power, by summing up the bonuses from all equipped items
        bonus = sum(equipment.power_bonus for equipment in self.owner.get_all_equipped())
        return self.base_power + bonus

    @property
    def defense(self):  # return actual defense, by summing up the bonuses from all equipped items
        bonus = sum(equipment.defense_bonus for equipment in self.owner.get_all_equipped())
        return self.base_defense + bonus

    @property
    def max_hp(self):  # return actual max_hp, by summing up the bonuses from all equipped items
        bonus = sum(equipment.max_hp_bonus for equipment in self.owner.get_all_equipped())
        return self.base_max_hp + bonus

    def attack(self, target):
        # a simple formula for attack damage
        damage = self.power - target.fighter.defense

        if damage > 0:
            # make the target take some damage
            message(self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' hit points.')
            target.fighter.take_damage(damage)
        else:
            message(self.owner.name.capitalize() + ' attacks ' + target.name + ' but it has no effect!')

    def take_damage(self, damage):
        # apply damage if possible
        if damage > 0:
            self.hp -= damage

            # check for death. if there's a death function, call it
            if self.hp <= 0:
                function = self.death_function
                if function is not None:
                    function(self.owner)

                if self.owner != player:  # yield experience to the player
                    player.fighter.xp += self.xp

    def heal(self, amount):
        # heal by the given amount, without going over the maximum
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp


# map stuff
class Tile:
    # a tile of the map and its properties
    def __init__(self, blocked, block_sight=None):
        self.explored = False
        self.blocked = blocked

        # by default, if a tile is blocked, it also blocks sight
        if block_sight is None: block_sight = blocked
        self.block_sight = block_sight


class Item:
    # an item that can be picked up and used.
    def __init__(self, use_function=None):
        self.use_function = use_function
        self.owner = None

    def pick_up(self):
        # add to the player's inventory and remove from the map
        if len(inventory) >= 26:
            message('Your inventory is full, cannot pick up ' + self.owner.name + '.', libtcod.red)
        else:
            inventory.append(self.owner)
            objects.remove(self.owner)
            message('You picked up a ' + self.owner.name + '!', libtcod.green)

            # special case: automatically equip, if the corresponding equipment slot is unused
            equipment = self.owner.equipment
            if equipment and self.owner.get_equipped_in_slot(equipment.slot) is None:
                equipment.equip()

    def drop(self):
        # special case: if the object has the Equipment component, dequip it before dropping
        if self.owner.equipment:
            self.owner.equipment.dequip()

        # add to the map and remove from the player's inventory. also, place it at the player's coordinates
        objects.append(self.owner)
        inventory.remove(self.owner)
        self.owner.x = player.x
        self.owner.y = player.y
        message('You dropped a ' + self.owner.name + '.', libtcod.yellow)

    def use(self):
        # special case: if the object has the Equipment component, the "use" action is to equip/dequip
        if self.owner.equipment:
            self.owner.equipment.toggle_equip()
            return

        # just call the "use_function" if it is defined
        if self.use_function is None:
            message('The ' + self.owner.name + ' cannot be used.')
        else:
            if self.use_function() != 'cancelled':
                inventory.remove(self.owner)  # destroy after use, unless it was cancelled for some reason


class Equipment:
    # an object that can be equipped, yielding bonuses. automatically adds the Item component.
    def __init__(self, slot, power_bonus=0, defense_bonus=0, max_hp_bonus=0):
        self.power_bonus = power_bonus
        self.defense_bonus = defense_bonus
        self.max_hp_bonus = max_hp_bonus

        self.slot = slot
        self.is_equipped = False
        self.owner = None

    def toggle_equip(self):  # toggle equip/dequip status
        if self.is_equipped:
            self.dequip()
        else:
            self.equip()

    def equip(self):
        # if the slot is already being used, dequip whatever is there first
        old_equipment = player.get_equipped_in_slot(self.slot)
        if old_equipment is not None:
            old_equipment.dequip()

        # equip object and show a message about it
        self.is_equipped = True
        message('Equipped ' + self.owner.name + ' on ' + self.slot + '.', libtcod.light_green)

    def dequip(self):
        # dequip object and show a message about it
        if not self.is_equipped: return
        self.is_equipped = False
        message('Dequipped ' + self.owner.name + ' from ' + self.slot + '.', libtcod.light_yellow)


class Rect:
    # a rectangle on the map. used to characterize a room.
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h

    def center(self):
        center_x = (self.x1 + self.x2) / 2
        center_y = (self.y1 + self.y2) / 2
        return (center_x, center_y)

    def intersect(self, other):
        # returns true if this rectangle intersects with another one
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)


def create_room(room):
    global map
    # go through the tiles in the rectangle and make them passable
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            map[x][y].blocked = False
            map[x][y].block_sight = False


def create_h_tunnel(x1, x2, y):
    global map
    for x in range(min(x1, x2), max(x1, x2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False


def create_v_tunnel(y1, y2, x):
    global map
    # vertical tunnel
    for y in range(min(y1, y2), max(y1, y2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False


def make_map():
    global map

    # fill map with "blocked" tiles
    map = [[Tile(True)
            for y in range(MAP_HEIGHT)]
           for x in range(MAP_WIDTH)]

    # create two rooms
    room1 = Rect(20, 15, 10, 15)
    room2 = Rect(50, 15, 10, 15)
    create_room(room1)
    create_room(room2)
    create_h_tunnel(25, 55, 23)
    player.x = 25
    player.y = 23


# runtime functions
def render_all():
    global fov_map, color_dark_wall, color_light_wall
    global color_dark_ground, color_light_ground
    global fov_recompute
    if fov_recompute:
        # recompute FOV if needed (the player moved or something)
        fov_recompute = False
        libtcod.map_compute_fov(fov_map, player.x, player.y, MAX_LIGHT_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)
        # go through all tiles, and set their background color according to the FOV
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                visible = libtcod.map_is_in_fov(fov_map, x, y)
                wall = map[x][y].block_sight
                if not visible:
                    # if it's not visible right now, the player can only see it if it's explored
                    if map[x][y].explored:
                        # it's out of the player's FOV
                        if wall:
                            libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET)
                        else:
                            libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET)
                else:
                    # it's visible
                    if wall:
                        libtcod.console_set_char_background(con, x, y, color_light_wall, libtcod.BKGND_SET)
                    else:
                        libtcod.console_set_char_background(con, x, y, color_light_ground, libtcod.BKGND_SET)
                    map[x][y].explored = True

    # draw all objects in the list, except the player. we want it to
    # always appear over all other objects! so it's drawn later.
    for object in objects:
        if object != player:
            object.draw()
    player.draw()

    # blit the contents of "con" to the root console and present it
    libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, MAP_Y)

    # prepare to render the GUI panel
    panel.clear(bg=libtcod.black)
    msg_panel.clear(bg=libtcod.black)

    # print the game messages, one line at a time
    m_y = 0
    for (line, color) in game_msgs:
        msg_panel.print(MSG_X, m_y, line, color)
        m_y += 1

    # show the player's stats
    render_bar(1, 1, BAR_WIDTH, 'HP', player.fighter.hp, player.fighter.max_hp,
               libtcod.light_red, libtcod.darker_red)
    panel.print(1, 3, 'Dungeon level ' + str(dungeon_level))

    # display names of objects under the mouse
    panel.print(1, 0, get_names_under_mouse(), bg=libtcod.light_gray)

    # blit the contents of "panel" to the root console
    libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)
    libtcod.console_blit(msg_panel, 0, 0, SCREEN_WIDTH, MSG_HEIGHT, 0, 0, 0)


def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
    # render a bar (HP, experience, etc). first calculate the width of the bar
    bar_width = int(float(value) / maximum * total_width)

    # render the background first
    panel.draw_rect(x, y, total_width, 1, False, bg=back_color)

    # now render the bar on top
    if bar_width > 0:
        panel.draw_rect(x, y, bar_width, 1, False, bg=back_color)

    # finally, some centered text with the values
    panel.print(int(x + total_width / 2), y, name + ': ' + str(value) + '/' + str(maximum), libtcod.white,
                alignment=libtcod.CENTER)


def get_names_under_mouse():
    # return a string with the names of all objects under the mouse
    mouse = libtcod.mouse_get_status()
    (x, y) = (mouse.cx, mouse.cy)

    # create a list with the names of all objects at the mouse's coordinates and in FOV
    names = [obj.name for obj in objects
             if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map, obj.x, obj.y)]

    names = ', '.join(names)  # join the names, separated by commas
    return names.capitalize()


def message(new_msg, color=libtcod.white):
    # split the message if necessary, among multiple lines
    new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)

    for line in new_msg_lines:
        # if the buffer is full, remove the first line to make room for the new one
        if len(game_msgs) == MSG_HEIGHT:
            del game_msgs[0]

        # add the new line as a tuple, with the text and the color
        game_msgs.append((line, color))


def msgbox(text, width=50):
    menu(text, [], width)  # use menu() as a sort of "message box"


def menu(header, options, width):
    if len(options) > 26: raise ValueError('Cannot have a menu with more than 26 options.')

    # calculate total height for the header (after auto-wrap) and one line per option
    header_height = con.get_height_rect(0, 0, width, SCREEN_HEIGHT, header)
    if header == '':
        header_height = 0
    height = len(options) + header_height

    # create an off-screen console that represents the menu's window
    window = libtcod.console_new(width, height)

    # print the header, with auto-wrap
    window.print_rect(0, 0, width, height, header)

    # print all the options
    y = header_height
    letter_index = ord('a')
    for option_text in options:
        text = '(' + chr(letter_index) + ') ' + option_text
        window.print(0, y, text)
        y += 1
        letter_index += 1

    # blit the contents of "window" to the root console
    x = int(SCREEN_WIDTH / 2 - width / 2)
    y = int(SCREEN_HEIGHT / 2 - height / 2)
    libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)

    # present the root console to the player and wait for a key-press
    libtcod.console_flush()
    key = libtcod.console_wait_for_keypress(True)

    if key.vk == libtcod.KEY_ENTER and key.lalt:  # (special case) Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    # convert the ASCII code to an index; if it corresponds to an option, return it
    index = key.c - ord('a')
    if index >= 0 and index < len(options): return index
    return None


def inventory_menu(header):
    # show a menu with each item of the inventory as an option
    if len(inventory) == 0:
        options = ['Inventory is empty.']
    else:
        options = []
        for item in inventory:
            text = item.name
            # show additional information, in case it's equipped
            if item.equipment and item.equipment.is_equipped:
                text = text + ' (on ' + item.equipment.slot + ')'
            options.append(text)

    index = menu(header, options, INVENTORY_WIDTH)

    # if an item was chosen, return it
    if index is None or len(inventory) == 0: return None
    return inventory[index].item


def handle_keys():
    global fov_recompute

    # key = libtcod.console_check_for_keypress()  #real-time
    key = libtcod.console_wait_for_keypress(True)  # turn-based

    if key.vk == libtcod.KEY_ENTER and key.lalt:
        # Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    elif key.vk == libtcod.KEY_ESCAPE:
        return STRING_EXIT  # exit game

    if game_state == STRING_PLAYING:
        # movement keys
        if libtcod.console_is_key_pressed(libtcod.KEY_UP):
            player.move(0, -1)
            fov_recompute = True

        elif libtcod.console_is_key_pressed(libtcod.KEY_DOWN):
            player.move(0, 1)
            fov_recompute = True

        elif libtcod.console_is_key_pressed(libtcod.KEY_LEFT):
            player.move(-1, 0)
            fov_recompute = True

        elif libtcod.console_is_key_pressed(libtcod.KEY_RIGHT):
            player.move(1, 0)
            fov_recompute = True
        else:
            # test for other keys
            key_char = chr(key.c)

            if key_char == 'g':
                # pick up an item
                for object in objects:  # look for an item in the player's tile
                    if object.x == player.x and object.y == player.y and object.item:
                        object.item.pick_up()
                        break

            if key_char == 'i':
                # show the inventory; if an item is selected, use it
                chosen_item = inventory_menu('Press the key next to an item to use it, or any other to cancel.\n')
                if chosen_item is not None:
                    chosen_item.use()

            if key_char == 'd':
                # show the inventory; if an item is selected, drop it
                chosen_item = inventory_menu('Press the key next to an item to drop it, or any other to cancel.\n')
                if chosen_item is not None:
                    chosen_item.drop()

            if key_char == 'c':
                # show character information
                level_up_xp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
                msgbox(
                    'Character Information\n\nLevel: ' + str(player.level) + '\nExperience: ' + str(player.fighter.xp) +
                    '\nExperience to level up: ' + str(level_up_xp) + '\n\nMaximum HP: ' + str(player.fighter.max_hp) +
                    '\nAttack: ' + str(player.fighter.power) + '\nDefense: ' + str(player.fighter.defense),
                    CHARACTER_SCREEN_WIDTH)

            if key_char == '<':
                # go down stairs, if the player is on them
                if stairs.x == player.x and stairs.y == player.y:
                    next_level()

            return STRING_NO_ACTION


def next_level():
    # advance to the next level
    global dungeon_level
    message('You take a moment to rest, and recover your strength.', libtcod.light_violet)
    player.fighter.heal(player.fighter.max_hp / 2)  # heal the player by 50%

    dungeon_level += 1
    message('After a rare moment of peace, you descend deeper into the heart of the dungeon...', libtcod.red)
    make_map()  # create a fresh new level!
    initialize_fov()


def initialize_fov():
    global fov_recompute, fov_map
    fov_recompute = True

    # create the FOV map, according to the generated map
    fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)

    libtcod.console_clear(con)  # unexplored areas start black (which is the default background color)


def player_death(pc):
    # the game ended!
    global game_state
    message('You died!', libtcod.red)
    game_state = 'dead'

    # for added effect, transform the player into a corpse!
    pc.char = '%'
    pc.color = libtcod.dark_red


def is_blocked(x, y):
    # first test the map tile
    if map[x][y].blocked:
        return True

    # now check for any blocking objects
    for object in objects:
        if object.blocks and object.x == x and object.y == y:
            return True

    return False


#############################################
# Initialization & Main Loop
#############################################
libtcod.console_set_custom_font('arial10x10.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
root = libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, "guess I'll die", False)
msg_panel = libtcod.console_new(SCREEN_WIDTH, MSG_HEIGHT)
con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)
panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)

img = libtcod.image_load('gidSmall.png')
while not libtcod.console_is_window_closed():
    # con.draw_rect(0, 0, SCREEN_WIDTH, SCREEN_WIDTH, True, fg=libtcod.white, bg=libtcod.white)
    libtcod.image_blit_2x(img, 0, int((SCREEN_WIDTH - int(img.width / 2)) / 2), 1)
    # show the game's title, and some credits!
    title_text = "GUESS I'LL DIE"
    x = int(SCREEN_WIDTH / 2) - (int(len(title_text) / 2))
    y = SCREEN_HEIGHT - 17
    con.print(x, y, title_text, libtcod.white, libtcod.black, libtcod.BKGND_OVERLAY)
    con.blit(root, x - 1, y - 1, x - 1, y - 1, len(title_text) + 2, 3)
    libtcod.console_flush(clear_color=libtcod.white)
    key = libtcod.console_wait_for_keypress(True)
    con.clear()

    # create an off-screen console that represents the menu's window
    # window = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)
    # libtcod.console_blit(window, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0, 1.0, 0.7)

    break

# create object representing the player
fighter_component = Fighter(hp=10, defense=1, power=2, xp=0, death_function=player_death)
player = Character(0, 0, '@', 'player', libtcod.white, blocks=True, fighter=fighter_component)

equipment_component = Equipment(slot='right hand', power_bonus=1)
obj = Object(0, 0, '-', 'rolled-up newspaper', libtcod.light_grey, equipment=equipment_component)
inventory.append(obj)
equipment_component.equip()
obj.always_visible = True

# the list of objects starting with the player
objects = [player]

# generate map (at this point it's not drawn to the screen)
make_map()

# generate field of view map based on level map
fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
for y in range(MAP_HEIGHT):
    for x in range(MAP_WIDTH):
        libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)

# global variables
fov_recompute = True
game_state = STRING_PLAYING
player_action = None

message('You are an elderly adventurer, come to the dungeon for one last quest. Recover the Golden Pigeon of Nyan!',
        libtcod.white)
libtcod.console_flush()

# main loop
while not libtcod.console_is_window_closed():

    # render the screen
    render_all()
    libtcod.console_flush()

    # erase all objects at their old locations, before they move
    for object in objects:
        object.clear()

    # handle keys and exit game if needed
    player_action = handle_keys()
    if player_action == STRING_EXIT:
        break
