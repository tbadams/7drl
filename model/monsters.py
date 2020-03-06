import tcod as libtcod
from util import random_choice_index, random_choice

default_color = libtcod.dark_red
templates = [("orc", 'O', libtcod.dark_green, 30, 2, 8, 100),
             ("goblin", 'g', libtcod.dark_green, 30, 2, 8, 100),
             ("demon", '&', libtcod.crimson, 30, 2, 8, 100),
             ("soldier ant", 'a', default_color, 30, 2, 8, 100),
             ("kobold", 'k', libtcod.purple, 30, 2, 8, 100),
             ("crocodile", 'C', libtcod.green, 30, 2, 8, 100),
             ("dragon", 'D', default_color, 30, 2, 8, 100),
             ("beaver", 'r', libtcod.dark_amber, 30, 2, 8, 100),
             ("hobgoblin", 'O', libtcod.orange, 30, 2, 8, 100),
             ("squirrel", 'r', libtcod.dark_orange, 30, 2, 8, 100),
             ("imp", 'i', default_color, 30, 2, 8, 100),
             ("shoggoth", '0', libtcod.black, 30, 2, 8, 100),
             ("xenomorph", '&', libtcod.black, 30, 2, 8, 100),
             ("bandit", 'B', libtcod.amber, 30, 2, 8, 100),
             ("pirate", 'P', default_color, 30, 2, 8, 100),
             ("ooze", '0', libtcod.light_green, 30, 2, 8, 100),
             ("Deep One", '&', libtcod.turquoise, 30, 2, 8, 100),
             ("giant squid", 'S', libtcod.pink, 30, 2, 8, 100),
             ("rat", 'r', libtcod.dark_yellow, 30, 2, 8, 100),
             ("snake", 's', libtcod.desaturated_green, 30, 2, 8, 100),
             ("ferret", 'f', libtcod.amber, 30, 2, 8, 100),
             ("wolf", 'w', libtcod.grey, 30, 2, 8, 100),
             ("warg", 'w', libtcod.black, 30, 2, 8, 100),
             ("troll", 'T', libtcod.dark_green, 30, 2, 8, 100),
             ("ogre", 'O', libtcod.light_turquoise, 30, 2, 8, 100),
             ("mind flayer", 'C', libtcod.purple, 30, 2, 8, 100),
             ("floating eye", 'E', libtcod.blue, 30, 2, 8, 100),
             ("gargoyle", '&', libtcod.dark_grey, 30, 2, 8, 100),
             ("zombie", 'z', libtcod.sepia, 30, 2, 8, 100),
             ("skeleton", 'z', libtcod.white, 30, 2, 8, 100),
             ("ghoul", 'z', libtcod.green, 30, 2, 8, 100),
             ("vampire", 'V', libtcod.dark_purple, 30, 2, 8, 100),
             ("werewolf", 'W', libtcod.light_orange, 30, 2, 8, 100),
             ("fox", 'f', libtcod.orange, 30, 2, 8, 100),
             ("bear", 'B', libtcod.darker_amber, 30, 2, 8, 100),
             ("velociraptor", 'v', default_color, 30, 2, 8, 100),
             ("ghost", 'G', libtcod.lightest_grey, 30, 2, 8, 100),
             ("unicorn", 'U', libtcod.white, 30, 2, 8, 100),
             ("boar", 'p', libtcod.darker_orange, 30, 2, 8, 100),
             ("cockatrice", 'c', libtcod.magenta, 30, 2, 8, 100),
             ("tiger", 'f', libtcod.orange, 30, 2, 8, 100),
             ("gremlin", 'i', libtcod.red, 30, 2, 8, 100),
             ("nymph", 'N', libtcod.sea, 30, 2, 8, 100),
             ("mimic", 'M', libtcod.gold, 30, 2, 8, 100),
             ("wumpus", 'W', libtcod.desaturated_purple, 30, 2, 8, 100),
             ("bat", 'b', libtcod.black, 30, 2, 8, 100),
             ("spider", 'x', libtcod.dark_purple, 30, 2, 8, 100),
             ("centaur", 'h', libtcod.dark_amber, 30, 2, 8, 100),
             ("giant", 'T', libtcod.orange, 30, 2, 8, 100),
             ("elemental", 'E', libtcod.desaturated_blue, 30, 2, 8, 100),
             ("titan", 'T', libtcod.magenta, 30, 2, 8, 100),
             ("minotaur", 'M', libtcod.dark_amber, 30, 2, 8, 100),
             ("lich", 'L', libtcod.light_pink, 30, 2, 8, 100),
             ("mummy", 'z', libtcod.yellow, 30, 2, 8, 100),
             ("naga", 'N', libtcod.dark_sea, 30, 2, 8, 100),
             ("necromancer", 'N', libtcod.violet, 30, 2, 8, 100),
             ("wraith", 'W', libtcod.light_turquoise, 30, 2, 8, 100),
             ("ape", 'A', libtcod.yellow, 30, 2, 8, 100),
             ("golem", 'G', libtcod.lightest_azure, 30, 2, 8, 100),
             ("newt", ':', libtcod.yellow, 30, 2, 8, 100),
             ("cyclops", '*', libtcod.light_green, 30, 2, 8, 100),
             ("chimera", '&', libtcod.green, 30, 2, 8, 100),
             ("hydra", 'S', libtcod.light_sea, 30, 2, 8, 100),
             ("harpy", 'h', libtcod.turquoise, 30, 2, 8, 100),
             ("satyr", 'h', libtcod.desaturated_amber, 30, 2, 8, 100),
             ("griffin", 'G', libtcod.gold, 30, 2, 8, 100),
             ("amazon", 'A', libtcod.yellow, 30, 2, 8, 100),
             ("sphinx", 'f', libtcod.gold, 30, 2, 8, 100),
             ("kraken", 'K', libtcod.dark_purple, 30, 2, 8, 100),
             ("basilisk", 'B', libtcod.dark_turquoise, 30, 2, 8, 100),
             ("chupacabra", '?', libtcod.red, 30, 2, 8, 100),
             ("manticore", 'M', libtcod.crimson, 30, 2, 8, 100),
             ("collossus", 'T', libtcod.brass, 30, 2, 8, 100),
             ("hippogriff", 'H', libtcod.red, 30, 2, 8, 100),
             ("kelpie", 'h', libtcod.cyan, 30, 2, 8, 100),
             ("pixie", 'F', libtcod.pink, 30, 2, 8, 100),
             ("wendigo", 'W', libtcod.light_turquoise, 30, 2, 8, 100),
             ("leprechaun", 'l', libtcod.green, 30, 2, 8, 100),
             ("gas spore", 'E', libtcod.green, 30, 2, 8, 100),
             ("quivering blob", 'Q', libtcod.desaturated_fuchsia, 30, 2, 8, 100),
             ("cobra", 's', libtcod.darkest_amber, 30, 2, 8, 100),
             ("pit viper", 's', libtcod.black, 30, 2, 8, 100),
             ("Barnie the Dinosaur", 'D', libtcod.purple),
             ("Ronald McDondald", 'R', libtcod.red),
             ("Grimace", 'G', libtcod.dark_purple),
             ("Hamburgler", 'H', libtcod.white),
             ("mime dressed as Adolf Hitler", 'H', libtcod.sepia),
             ("Saskatchewan, Canada", 'A', libtcod.light_red),
             ("Great God Cthulhu", 'C', libtcod.dark_green),
             ("clown", 'C', libtcod.white),
             ("murder clown", 'C', libtcod.crimson),
             ("hobo clown", 'C', libtcod.dark_orange),
             ("Franz Kafka", "K", libtcod.darkest_crimson),
             ("Pullitzer Prize-winning author and film critic Roger Ebert", 'E', libtcod.light_grey),
             ("Grey", 'g', libtcod.grey),
             ("gladiator", 'g', libtcod.gold),
             ("wampa", 'W', libtcod.white)
             ]


def make_enemy(floor):
    template = random_choice_index(templates)


def display_test(con, width, height):
    con.clear(bg=libtcod.lightest_grey)
    templates.sort(key=lambda t: (t[1], t[2]))
    i = 0
    for y in range(0, height):
        for x in range(0, width):
            if i >= len(templates):
                break
            t = templates[i]
            con.print(x, y, t[1], t[2])
            i += 1
    libtcod.console_flush()
    libtcod.console_wait_for_keypress(True)
