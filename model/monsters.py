import tcod as libtcod
from util import random_choice_index, random_choice
from model.character import Character, Fighter


class BasicMonster:
    def take_turn(self, target, fov_map, game_map, entities):
        results = []

        monster = self.owner
        if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):

            if monster.distance_to(target) >= 2:
                monster.move_astar(target, entities, game_map)

            elif target.fighter.hp > 0:
                attack_results = monster.fighter.attack(target)
                results.extend(attack_results)

        return results


class MT:
    def __init__(self, name, char, color):
        self.name = name
        self.char = char
        self.color = color

    def to_args(self):  # sigh
        return self.char, self.name, self.color


default_color = libtcod.dark_red
templates = [MT("orc", 'O', libtcod.dark_green),
             MT("goblin", 'g', libtcod.dark_green),
             MT("demon", '&', libtcod.crimson),
             MT("soldier ant", 'a', default_color),
             MT("kobold", 'k', libtcod.purple),
             MT("crocodile", 'C', libtcod.green),
             MT("dragon", 'D', default_color),
             MT("beaver", 'r', libtcod.dark_amber),
             MT("hobgoblin", 'O', libtcod.orange),
             MT("squirrel", 'r', libtcod.dark_orange),
             MT("imp", 'i', default_color),
             MT("shoggoth", '0', libtcod.black),
             MT("xenomorph", '&', libtcod.black),
             MT("bandit", 'B', libtcod.amber),
             MT("pirate", 'P', default_color),
             MT("ooze", '0', libtcod.light_green),
             MT("Deep One", '&', libtcod.turquoise),
             MT("giant squid", 'S', libtcod.pink),
             MT("rat", 'r', libtcod.dark_yellow),
             MT("snake", 's', libtcod.desaturated_green),
             MT("ferret", 'f', libtcod.amber),
             MT("wolf", 'w', libtcod.grey),
             MT("warg", 'w', libtcod.black),
             MT("troll", 'T', libtcod.dark_green),
             MT("ogre", 'O', libtcod.light_turquoise),
             MT("mind flayer", 'C', libtcod.purple),
             MT("floating eye", 'E', libtcod.blue),
             MT("gargoyle", '&', libtcod.dark_grey),
             MT("zombie", 'z', libtcod.sepia),
             MT("skeleton", 'z', libtcod.white),
             MT("ghoul", 'z', libtcod.green),
             MT("vampire", 'V', libtcod.dark_purple),
             MT("werewolf", 'W', libtcod.light_orange),
             MT("fox", 'f', libtcod.orange),
             MT("bear", 'B', libtcod.darker_amber),
             MT("velociraptor", 'v', default_color),
             MT("ghost", 'G', libtcod.lightest_grey),
             MT("unicorn", 'U', libtcod.white),
             MT("boar", 'p', libtcod.darker_orange),
             MT("cockatrice", 'c', libtcod.magenta),
             MT("tiger", 'f', libtcod.orange),
             MT("gremlin", 'i', libtcod.red),
             MT("nymph", 'N', libtcod.sea),
             MT("mimic", 'M', libtcod.gold),
             MT("wumpus", 'W', libtcod.desaturated_purple),
             MT("bat", 'b', libtcod.black),
             MT("spider", 'x', libtcod.dark_purple),
             MT("centaur", 'h', libtcod.dark_amber),
             MT("giant", 'T', libtcod.orange),
             MT("elemental", 'E', libtcod.desaturated_blue),
             MT("titan", 'T', libtcod.magenta),
             MT("minotaur", 'M', libtcod.dark_amber),
             MT("lich", 'L', libtcod.light_pink),
             MT("mummy", 'z', libtcod.yellow),
             MT("naga", 'N', libtcod.dark_sea),
             MT("necromancer", 'N', libtcod.violet),
             MT("wraith", 'W', libtcod.light_turquoise),
             MT("ape", 'A', libtcod.yellow),
             MT("golem", 'G', libtcod.lightest_azure),
             MT("newt", ':', libtcod.yellow),
             MT("cyclops", '*', libtcod.light_green),
             MT("chimera", '&', libtcod.green),
             MT("hydra", 'S', libtcod.light_sea),
             MT("harpy", 'h', libtcod.turquoise),
             MT("satyr", 'h', libtcod.desaturated_amber),
             MT("griffin", 'G', libtcod.gold),
             MT("amazon", 'A', libtcod.yellow),
             MT("sphinx", 'f', libtcod.gold),
             MT("kraken", 'K', libtcod.dark_purple),
             MT("basilisk", 'B', libtcod.dark_turquoise),
             MT("chupacabra", '?', libtcod.red),
             MT("manticore", 'M', libtcod.crimson),
             MT("collossus", 'T', libtcod.brass),
             MT("hippogriff", 'H', libtcod.red),
             MT("kelpie", 'h', libtcod.cyan),
             MT("pixie", 'F', libtcod.pink),
             MT("wendigo", 'W', libtcod.light_turquoise),
             MT("leprechaun", 'l', libtcod.green),
             MT("gas spore", 'E', libtcod.green),
             MT("quivering blob", 'Q', libtcod.desaturated_fuchsia),
             MT("cobra", 's', libtcod.darkest_amber),
             MT("pit viper", 's', libtcod.black),
             MT("Barnie the Dinosaur", 'D', libtcod.purple),
             MT("Ronald McDondald", 'R', libtcod.red),
             MT("Grimace", 'G', libtcod.dark_purple),
             MT("Hamburgler", 'H', libtcod.white),
             MT("mime dressed as Adolf Hitler", 'H', libtcod.sepia),
             MT("Saskatchewan, Canada", 'A', libtcod.light_red),
             MT("Great God Cthulhu", 'C', libtcod.dark_green),
             MT("clown", 'C', libtcod.white),
             MT("murder clown", 'C', libtcod.crimson),
             MT("hobo clown", 'C', libtcod.dark_orange),
             MT("Franz Kafka", "K", libtcod.darkest_crimson),
             MT("Pullitzer Prize-winning author and film critic Roger Ebert", 'E', libtcod.light_grey),
             MT("grey", 'g', libtcod.grey),
             MT("gladiator", 'g', libtcod.gold),
             MT("wampa", 'W', libtcod.white),
             MT("Sue the T-Rex", 'D', libtcod.dark_yellow)
             ]


def make_enemy(x, y, floor):
    template = random_choice_index(templates)
    fighter_component = Fighter(hp=20, defense=0, power=4, xp=35)
    ai_component = BasicMonster()
    enemy = Character(x, y, fighter=fighter_component, *template.to_args())
    return enemy


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
