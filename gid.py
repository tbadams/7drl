import random
import shelve
import textwrap
from enum import Enum, auto

import tcod as libtcod
import tcod.event

from map import make_map, cardinal_names
from model.character import Character, Fighter
from model.death import Death
from model.object import Object
from util import pad

import os
import sys

# print(sys.path)

VERSION = "1.1.1"

ASSET_DIR = "assets"

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

MENU_WIDTH = 24

# fov
FOV_ALGO = 0  # default FOV algorithm
FOV_LIGHT_WALLS = True
MAX_LIGHT_RADIUS = 10

LIMIT_FPS = 20  # 20 frames-per-second maximum

# action strings
STRING_EXIT = 'exit'
STRING_NO_ACTION = 'didnt-take-turn'
STRING_ACTION = 'took-turn'

# game state strings

GS_PLAYING = 'playing'
GS_DEAD = 'dead'

# experience and level-ups
LEVEL_UP_BASE = 200
LEVEL_UP_FACTOR = 150
DLEVEL_SCORE = 100
DLEVEL_XP = 10

# colors
color_dark_wall = libtcod.Color(0, 0, 100)
color_dark_ground = libtcod.Color(50, 50, 150)
color_light_wall = libtcod.Color(200, 180, 50)
color_light_ground = libtcod.Color(130, 110, 50)

INVENTORY_MAX = 26
WALL_DMG = 10
OBAMA_CHANCE = 0.1

SCORES_FILE_NAME = "scores.json"
SCORE_KEY = "score"
ACHEIVEMENTS_FILE_NAME = "acheive.json"

# game state
game_msgs = []
inventory = []
player = None
fov_recompute = None
game_state = None
fov_map = None
game = None
dungeon_map = None

bundle_dir = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS


def get_asset_filepath(filename):
    return bundle_dir + os.sep + ASSET_DIR + os.sep + filename


class Screen(Enum):
    MAIN_MENU = auto()
    GAME = auto()
    TOMBSTONE = auto()
    SCORES = auto()


class GameState:

    def __init__(self):
        self.score = 0
        self.time = 0
        self.discovered = {}


# player, inventory
def attack_menu(pc):
    global dungeon_map, player
    targets = []
    for i in range(-1, 2):
        for j in range(-1, 2):
            stuff = dungeon_map.get_stuff(pc.x + i, pc.y + j)
            targets += filter(lambda o: o.fighter and o != player, stuff)
    if len(targets) == 0:
        message("You can't hit that.", libtcod.white)
    else:
        target_choice = menu("Attack:",
                             list(map(lambda o: o.name + " (" + cardinal_names(o.x - pc.x, o.y - pc.y) + ")", targets)))
        if target_choice is not None:
            return targets[target_choice]
        return None


def move(thing, dx, dy):
    # move by the given amount if not blocked
    global dungeon_map
    target_x = thing.x + dx
    target_y = thing.y + dy
    if not dungeon_map.is_blocked(target_x, target_y):
        thing.x += dx
        thing.y += dy
    elif thing is player:
        possible_blockers = dungeon_map.get_stuff(target_x, target_y)
        blocker = None
        if len(possible_blockers) > 0:
            blocker = possible_blockers[0]
        blocker_name = "a wall"
        if blocker is not None:
            blocker_name = str(blocker)
        message("Ouch! You blunder into " + blocker_name + ".", libtcod.orange)
        player.fighter.take_damage(random.randint(1, 5), "running into " + blocker_name)


def pick_up(item):
    global dungeon_map, player
    # add to the player's inventory and remove from the map
    if len(inventory) >= 26:
        message('You attempt to pick up ' + item.owner.name + ', but are crushed under the weight of your load.',
                libtcod.orange)
        player.take_damage(111, "crushed to death")
    else:
        inventory.append(item.owner)
        dungeon_map.objects.remove(item.owner)
        message('You picked up ' + item.owner.name + '.', libtcod.white)

        # special case: automatically equip, if the corresponding equipment slot is unused
        equipment = item.owner.equipment
        if equipment and player.get_equipped_in_slot(equipment.slot) is None:
            equipment.equip()


def drop(item):
    global dungeon_map
    # special case: if the object has the Equipment component, dequip it before dropping
    if item.owner.equipment:
        item.owner.equipment.dequip()

    # add to the map and remove from the player's inventory. also, place it at the player's coordinates
    dungeon_map.objects.append(item.owner)
    inventory.remove(item.owner)
    item.owner.x = player.x
    item.owner.y = player.y
    message('You dropped a ' + item.owner.name + '.', libtcod.yellow)


def use(item):
    global player
    # special case: if the object has the Equipment component, the "use" action is to equip/dequip
    if item.owner.equipment:
        item.owner.equipment.toggle_equip()
        return

    # just call the "use_function" if it is defined
    if item.use_function is None:
        message('The ' + item.owner.name + ' cannot be used.')
    else:
        result = item.use_function(player)
        if result != 'cancelled':
            inventory.remove(item.owner)  # destroy after use, unless it was cancelled for some reason
            for msg in result:
                message(*msg.as_args())


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


# runtime functions
def render_all():
    global fov_map, color_dark_wall, color_light_wall
    global color_dark_ground, color_light_ground
    global fov_recompute, dungeon_map
    if fov_recompute:
        # recompute FOV if needed (the player moved or something)
        fov_recompute = False
        libtcod.map_compute_fov(fov_map, player.x, player.y, MAX_LIGHT_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)
        # go through all tiles, and set their background color according to the FOV
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                visible = libtcod.map_is_in_fov(fov_map, x, y)
                wall = dungeon_map.tiles[x][y].block_sight
                if not visible:
                    # if it's not visible right now, the player can only see it if it's explored
                    if dungeon_map.tiles[x][y].explored:
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
                    dungeon_map.tiles[x][y].explored = True

    # draw all objects in the list, except the player. we want it to
    # always appear over all other objects! so it's drawn later.
    cache = {}
    for o in dungeon_map.objects:
        if o != player:
            coords = o.x, o.y
            if coords not in cache or cache[coords].layer() <= o.layer():
                o.draw(con, fov_map)
                cache[coords] = o

    player.draw(con, fov_map)

    # blit the contents of "con" to the root console and present it
    libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, MAP_Y)

    # prepare to render the GUI panel
    panel.clear(bg=libtcod.darkest_grey)
    msg_panel.clear(bg=libtcod.black)

    # print the game messages, one line at a time
    m_y = 0
    for (line, color) in game_msgs:
        msg_panel.print(MSG_X, m_y, line, color)
        m_y += 1

    # show the player's stats
    panel.print(1, 1, 'HP: ' + str(player.fighter.hp) + "/" + str(player.fighter.max_hp),
                libtcod.white)
    panel.print(1, 2, player.name + '     Score: ' + str(game.score))
    panel.print(1, 3, 'Dungeon level ' + str(dungeon_map.dungeon_level))

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
    global dungeon_map, fov_map
    mouse = libtcod.mouse_get_status()
    (x, y) = (mouse.cx, mouse.cy)

    # create a list with the names of all objects at the mouse's coordinates and in FOV
    names = [obj.name for obj in dungeon_map.objects
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


def msgbox(text, width=50, wait_for_key=True):
    menu(text, [], width, wait_for_key=wait_for_key)  # use menu() as a sort of "message box"


def text_entry(text, width=50):
    text_height = 0
    if text != '':
        text_height = con.get_height_rect(0, 0, width, SCREEN_HEIGHT, text)
    height = text_height + 3
    window = libtcod.console_new(width, height)
    # blit the contents of "window" to the root console
    x = int(SCREEN_WIDTH / 2 - width / 2)
    y = int(SCREEN_HEIGHT / 2 - height / 2)

    user_input = ""
    while not libtcod.console_is_window_closed():
        window.print_rect(0, 0, width, height, text)
        libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 1.0)
        libtcod.console_flush()
        k = libtcod.console_wait_for_keypress(True)
        text_len = len(user_input)
        if k.vk == tcod.KEY_CHAR:
            cat = chr(k.c)
            if libtcod.console_is_key_pressed(libtcod.KEY_SHIFT):
                cat = cat.capitalize()
            user_input += cat
        elif k.vk == tcod.KEY_SPACE:
            user_input += " "
        elif k.vk == tcod.KEY_BACKSPACE:
            if text_len > 0:
                user_input = user_input[0:text_len - 1]
        elif k.vk == tcod.KEY_ENTER:
            if text_len > 0:
                return user_input
        window.clear()
        window.print(0, text_height + 2, user_input)


def menu(header, options, width=50, y_adjust=0, wait_for_key=True):
    if len(options) > 26:
        raise ValueError('Cannot have a menu with more than 26 options.')

    # calculate total height for the header (after auto-wrap) and one line per option
    header_height = con.get_height_rect(0, 0, width, SCREEN_HEIGHT, header)
    if header == '':
        header_height = 0
    height = len(options) + header_height

    # new temp console
    window = libtcod.console_new(width, height)
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
    y = int(SCREEN_HEIGHT / 2 - height / 2) + y_adjust
    libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)

    # present the root console to the player and wait for a key-press
    libtcod.console_flush()
    if wait_for_key:
        key = libtcod.console_wait_for_keypress(True)

        if key.vk == libtcod.KEY_ENTER and key.lalt:  # (special case) Alt+Enter: toggle fullscreen
            libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

        # convert the ASCII code to an index; if it corresponds to an option, return it
        index = key.c - ord('a')
        if 0 <= index < len(options):
            return index
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
    global fov_recompute, screen, dungeon_map, player

    key = libtcod.console_wait_for_keypress(True)

    if key.vk == libtcod.KEY_ENTER and key.lalt:
        # toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    elif key.vk == libtcod.KEY_ESCAPE:
        confirm = menu("Abandon the quest?", ["Yes", "No"], MENU_WIDTH)
        if confirm == 0:
            screen = Screen.MAIN_MENU
            player_death(player, "quit")
            return STRING_EXIT
        return STRING_NO_ACTION

    if game_state == GS_PLAYING:
        # movement keys
        if key.vk == libtcod.KEY_UP:
            move(player, 0, -1)
            fov_recompute = True
            return STRING_ACTION

        elif libtcod.console_is_key_pressed(libtcod.KEY_DOWN):
            move(player, 0, 1)
            fov_recompute = True
            return STRING_ACTION

        elif libtcod.console_is_key_pressed(libtcod.KEY_LEFT):
            move(player, -1, 0)
            fov_recompute = True
            return STRING_ACTION

        elif libtcod.console_is_key_pressed(libtcod.KEY_RIGHT):
            move(player, 1, 0)
            fov_recompute = True
            return STRING_ACTION
        elif libtcod.console_is_key_pressed(libtcod.KEY_INSERT):
            move(player, -1, -1)
            fov_recompute = True
            return STRING_ACTION
        elif libtcod.console_is_key_pressed(libtcod.KEY_HOME):
            move(player, 1, -1)
            fov_recompute = True
            return STRING_ACTION
        elif libtcod.console_is_key_pressed(libtcod.KEY_END):
            move(player, 1, 1)
            fov_recompute = True
            return STRING_ACTION
        elif libtcod.console_is_key_pressed(libtcod.KEY_DELETE):
            move(player, -1, 1)
            fov_recompute = True
            return STRING_ACTION
        else:
            # test for other keys
            key_char = chr(key.c)

            if key_char == 'a':
                target = attack_menu(player)
                if target:
                    for msg in player.fighter.attack(player, target):
                        as_args = msg.as_args()
                        message(*as_args)
                    return STRING_ACTION
                else:
                    return STRING_NO_ACTION

            if key_char == 'g':
                # pick up an item
                for object in dungeon_map.objects:  # look for an item in the player's tile
                    if object.x == player.x and object.y == player.y and object.item:
                        pick_up(object.item)
                        return STRING_ACTION
                return STRING_NO_ACTION

            if key_char == 'i':
                # show the inventory; if an item is selected, use it
                chosen_item = inventory_menu('Use item:\n')
                if chosen_item is not None:
                    use(chosen_item)
                    return STRING_ACTION
                else:
                    return STRING_NO_ACTION

            if key_char == 'd':
                # show the inventory; if an item is selected, drop it
                chosen_item = inventory_menu('Drop item:\n')
                if chosen_item is not None:
                    drop(chosen_item)
                    return STRING_ACTION
                else:
                    return STRING_NO_ACTION

            if key_char == 'c':
                # show character information
                level_up_xp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
                msgbox(
                    'Character Information\n\nLevel: ' + str(player.level) + '\nExperience: ' + str(player.fighter.xp) +
                    '\nExperience to level up: ' + str(level_up_xp) + '\n\nMaximum HP: ' + str(player.fighter.max_hp) +
                    '\nAttack: ' + str(player.fighter.power) + '\nDefense: ' + str(player.fighter.defense),
                    CHARACTER_SCREEN_WIDTH)
                return STRING_NO_ACTION
            if key_char == 'l':
                # while True:
                #     render_all()
                return STRING_NO_ACTION
            if key_char == '/' and key.shift:
                show_help()
                return STRING_NO_ACTION
            if key_char == '.' and key.shift:  # >
                # go down stairs, if the player is on them
                if dungeon_map.stairs_down.x == player.x and dungeon_map.stairs_down.y == player.y:
                    next_level()
                    return STRING_ACTION
                else:
                    message("You can't go down on that.", libtcod.white)
                    return STRING_NO_ACTION
            if key_char == '.' and not key.shift:
                return STRING_ACTION  # wait

            if key_char == ',' and key.shift:  # <
                if dungeon_map.stairs_up.x == player.x and dungeon_map.stairs_up.y == player.y:
                    message("You attempt to climb the stairs but the effort destroys your already frail body.",
                            libtcod.yellow)
                    player.fighter.take_damage(100, "collapsed from over-exertion")
                    return STRING_ACTION
                else:
                    message("You can't get high here.", libtcod.white)
                    return STRING_NO_ACTION
            else:
                print(key)
                return STRING_NO_ACTION

            return STRING_ACTION
    elif game_state == GS_DEAD:
        screen = Screen.TOMBSTONE
        return STRING_EXIT


def show_help():
    msgbox("Controls:\n\n"
           "ARROWS    = NESW MOVEMENT\n"
           "INSERT    = NW\n"
           "HOME      = NE\n"
           "END       = SE\n"
           "DELETE    = SW\n"
           "a         = ATTACK\n"
           "i         = INVENTORY\n"
           "c         = CHARACTER SCREEN\n"
           "g         = GET ITEMS\n"
           "d         = DROP ITEMS\n"
           # "l      = LOOK (MOUSE)\n"
           "<         = GO UP\n"
           ">         = GO DOWN\n"
           ".         = NO ACTION\n"
           "?         = THIS MESSAGE\n"
           "ALT+ENTER = FULL SCREEN\n")


def next_level():
    # advance to the next level
    global dungeon_map, player, game

    player.fighter.xp += DLEVEL_XP * dungeon_map.dungeon_level
    game.score += DLEVEL_SCORE * dungeon_map.dungeon_level
    next_dlevel = dungeon_map.dungeon_level + 1
    if random.random() < 0.1:
        message("You tumble down the stairs.", libtcod.orange)
        player.fighter.take_damage(random.randint(1, 4), "fell down the stairs")
    else:
        message('You manage to avoid falling down the stairs.', libtcod.white)
    dungeon_map = make_map(MAP_WIDTH, MAP_HEIGHT, player)
    dungeon_map.dungeon_level = next_dlevel
    initialize_fov()


def initialize_fov():
    global fov_recompute, fov_map
    fov_recompute = True

    # create the FOV map, according to the generated map
    fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            libtcod.map_set_properties(fov_map, x, y, not dungeon_map.tiles[x][y].block_sight,
                                       not dungeon_map.tiles[x][y].blocked)

    libtcod.console_clear(con)  # unexplored areas start black (which is the default background color)


def player_death(pc, death_text):
    # the game ended!
    global game_state, dungeon_map
    died_txt = 'You died!'
    if random.random() < OBAMA_CHANCE:
        died_txt = "THANKS OBAMA"
    message(died_txt, libtcod.red)
    game_state = GS_DEAD
    player.death = Death(player, death_text, game, dungeon_map)
    # corpse time
    pc.char = '%'
    pc.color = libtcod.dark_red

    # save to high score
    shelf = shelve.open(SCORES_FILE_NAME)
    scores = []
    if SCORE_KEY in shelf:
        scores = shelf[SCORE_KEY]
    scores.append(player)
    scores.sort(reverse=True, key=lambda dead_person: (
        dead_person.death.game.score, dead_person.level, dead_person.death.floor.dungeon_level, dead_person.name))
    shelf[SCORE_KEY] = scores
    shelf.close()


def load_scores():
    shelf = shelve.open(SCORES_FILE_NAME)
    scores = []
    if SCORE_KEY in shelf:
        scores = shelf[SCORE_KEY]
    shelf.close()
    return scores


def tombstone():
    global player, game, dungeon_map
    death = player.death
    death_screen = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)
    death_screen.clear(bg=libtcod.black)
    tombstone_lines = [
        "----------\n",
        "/          \\\n",
        "/    REST    \\\n",
        "/      IN      \\\n",
        "/     PEACE      \\\n",
        "/                  \\\n"
    ]
    grave_width = 16
    x_coord = int(SCREEN_WIDTH / 2)
    y_start = 10
    y_coord = y_start
    top_lines = len(tombstone_lines)
    tombstone_lines.append(player.name)
    tombstone_lines.append("Score: " + str(death.game.score))
    tombstone_lines.append("Dungeon Level: " + str(death.floor.dungeon_level))
    tombstone_lines.append("")
    tombstone_lines = tombstone_lines + textwrap.wrap(death.epitath, grave_width)
    for i in range(0, MSG_HEIGHT + 1):
        tombstone_lines.append("")
    for line in tombstone_lines:
        death_screen.print(x_coord, y_coord, line, libtcod.white, alignment=libtcod.CENTER)
        y_coord += 1

    for i in range(top_lines + y_start, y_coord):
        death_screen.print(int((SCREEN_WIDTH / 2) - (grave_width / 2) - 2), i, "|", libtcod.white)
        death_screen.print(int((SCREEN_WIDTH / 2) + (grave_width / 2) + 1), i, "|", libtcod.white)
    bottom = ""
    for i in range(0, grave_width * 2):
        bottom += "-"
        death_screen.print(x_coord, y_coord, bottom, libtcod.white, alignment=libtcod.CENTER)

    death_screen.blit(root)
    libtcod.console_flush()
    libtcod.console_wait_for_keypress(True)


def show_scores():
    root.clear(bg=libtcod.black)
    msgbox("LOADING...", 10, False)
    x_coord = 1
    y_start = 0
    rank = 1
    scores = load_scores()
    for dead_person in scores:
        y_coord = rank + y_start
        num_txt = pad(str(rank) + ". ", 5)
        score_txt = pad(str(dead_person.death.game.score) + "   ", 8)
        name_txt = pad(dead_person.name + "   ", 18)
        epitath_txt = pad(dead_person.death.epitath,
                          SCREEN_WIDTH - x_coord - len(num_txt) - len(score_txt) - len(name_txt))
        root.print(x_coord, y_coord, num_txt + score_txt + name_txt + epitath_txt, libtcod.white)
        rank += 1
    libtcod.console_flush()
    libtcod.console_wait_for_keypress(True)


def new_game():
    global player, fov_recompute, game_state, fov_map, game, game_msgs, inventory, dungeon_map, screen

    root.clear(bg=libtcod.black)
    libtcod.console_flush()
    name = text_entry("You are an elderly adventurer, come to the dungeon for one last quest."
                      "\n\nWhat is your name, wizened one?")

    inventory = []
    dungeon_level = 1

    # player
    fighter_component = Fighter(hp=10, defense=1, power=2, xp=0, death_function=player_death)
    player = Character(0, 0, '@', name, libtcod.white, fighter=fighter_component, inventory=inventory, player=True)
    equipment_component = Equipment(slot='right hand', power_bonus=2)
    obj = Object(0, 0, '/', 'rolled-up newspaper', libtcod.light_grey, equipment=equipment_component)
    inventory.append(obj)
    equipment_component.equip()
    obj.always_visible = True

    # generate map (at this point it's not drawn to the screen)
    dungeon_map = make_map(MAP_WIDTH, MAP_HEIGHT, player)

    # generate field of view map based on level map
    fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            libtcod.map_set_properties(fov_map, x, y, not dungeon_map.tiles[x][y].block_sight,
                                       not dungeon_map.tiles[x][y].blocked)

    # global variables
    fov_recompute = True
    game_state = GS_PLAYING
    game = GameState()

    game_msgs = []
    message("Go, " + player.name + "! Recover the Golden Pigeon of Nyan!", libtcod.white)
    message("Press '?' for help", libtcod.grey)
    main_loop()


def main_loop():
    global dungeon_map, game
    while not libtcod.console_is_window_closed():

        # render the screen
        render_all()
        libtcod.console_flush()

        # erase all objects at their old locations, before they move
        for o in dungeon_map.objects:
            o.clear(con)

        # handle keys and exit game if needed
        player_action = handle_keys()
        if player_action == STRING_EXIT:
            break
        elif player_action != STRING_NO_ACTION:
            game.time += 1
            if game.time % 10 == 0:  # Score from time survived
                game.score += 1
            # npc turns
            for entity in dungeon_map.objects:
                if entity.ai:
                    enemy_turn_results = entity.ai.take_turn(player, fov_map, dungeon_map)
                    for result in enemy_turn_results:
                        message(*result.as_args())
        else:
            print("defer turn")


def print_title(img):
    root.clear(fg=libtcod.white, bg=libtcod.white)
    libtcod.image_blit_2x(img, 0, int((SCREEN_WIDTH - int(img.width / 2)) / 2), 2)
    root.print(0, SCREEN_HEIGHT - 1, "By Dogsonofawolf", libtcod.black, libtcod.white)
    version_txt = "VERSION " + VERSION
    root.print(SCREEN_WIDTH - len(version_txt) - 1, SCREEN_HEIGHT - 1, version_txt, libtcod.black, libtcod.white)


#############################################
# Initialization & Main Loop
#############################################
libtcod.console_set_custom_font(get_asset_filepath('arial10x10.png'), libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
root = libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, "guess I'll die", False)
msg_panel = libtcod.console_new(SCREEN_WIDTH, MSG_HEIGHT)
con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)
panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)
screen = Screen.MAIN_MENU
while not libtcod.console_is_window_closed():
    if screen == Screen.MAIN_MENU:
        img = libtcod.image_load(get_asset_filepath('gidSmall.png'))
        print_title(img)
        title_text = "GUESS I'LL DIE"
        x = int(SCREEN_WIDTH / 2) - (int(len(title_text) / 2))
        y = SCREEN_HEIGHT - 18
        con.clear(bg=libtcod.black)
        con.print(x, y, title_text, libtcod.white, libtcod.black, libtcod.BKGND_OVERLAY)
        con.blit(root, x - 1, y - 1, x - 1, y - 1, len(title_text) + 2, 3, bg_alpha=0.7)
        libtcod.console_flush(clear_color=libtcod.white)
        key = libtcod.console_wait_for_keypress(True)
        con.clear(bg=libtcod.black)
        print_title(img)

        # create an off-screen console that represents the menu's window
        choice = menu("\n " + title_text + "\n", ['NEW GAME', 'SCORES', 'QUIT'], 16, 10)
        if choice is 0:
            screen = Screen.GAME
        elif choice is 1:
            screen = Screen.SCORES
        elif choice is 2:
            break
        # else:
        #     display_test(root, SCREEN_WIDTH, SCREEN_HEIGHT)
        #     screen = Screen.MAIN_MENU
    elif screen == Screen.GAME:
        new_game()
    elif screen == Screen.TOMBSTONE:
        tombstone()
        screen = Screen.SCORES
    elif screen == Screen.SCORES:
        show_scores()
        player = None  # clean up
        screen = Screen.MAIN_MENU
