import math
import random

import tcod as libtcod

from model.object import Object, Layer
from msg import Message
from util import random_choice_index


def default_death(monster, death_text):
    death_message = Message('{0} dies.'.format(monster.name.capitalize()), libtcod.red)

    monster.char = '%'
    # monster.color = libtcod.dark_red
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = 'corpse (' + monster.name + ')'
    monster.render_order = Layer.TRASH

    return death_message


class Character(Object):
    def __init__(self, x, y, char, name, color, fighter, ai=None, inventory=None, player=False):
        super().__init__(x, y, char, name, color, True, fighter=fighter)
        if self.fighter:
            fighter.owner = self
        else:
            raise Exception("No fighter in character")
        if inventory is None:
            inventory = []
        self.inventory = inventory
        self.player = player
        self.ai = ai
        if self.ai:
            self.ai.owner = self

        self.level = 1
        self.death = None

    def __str__(self):
        return self.name

    def get_all_equipped(self):  # returns a list of equipped items
        equipped_list = []
        for item in self.inventory:
            if item.equipment and item.equipment.is_equipped:
                equipped_list.append(item.equipment)
        return equipped_list

    def get_equipped_in_slot(self, slot):  # returns the equipment in a slot, or None if it's empty
        for obj in self.inventory:
            if obj.equipment and obj.equipment.slot == slot and obj.equipment.is_equipped:
                return obj.equipment
        return None

    def move_towards(self, target_x, target_y, dungeon_map):
        entities = dungeon_map.objects
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)

        dx = int(round(dx / distance))
        dy = int(round(dy / distance))

        if not (dungeon_map.is_blocked(self.x + dx, self.y + dy) or
                get_blocking_entities_at_location(entities, self.x + dx, self.y + dy)):
            return self.move(dx, dy, dungeon_map)
        return []

    def move(self, dx, dy, dungeon_map):
        # move by the given amount if not blocked
        target_x = self.x + dx
        target_y = self.y + dy
        if not dungeon_map.is_blocked(target_x, target_y):
            self.x += dx
            self.y += dy
        else:
            possible_blockers = dungeon_map.get_stuff(target_x, target_y)
            blocker = None
            if len(possible_blockers) > 0:
                blocker = possible_blockers[0]
            blocker_name = "a wall"
            if blocker is not None:
                blocker_name = str(blocker)
            msgs = [Message(self.name + "slams into " + blocker_name + ".", libtcod.orange)]
            msgs.extend(self.fighter.take_damage(random.randint(1, 5), "running into " + blocker_name))
            return msgs
        return []

    def distance(self, x, y):
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)

    def distance_to(self, other):
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)

    def move_astar(self, target, dungeon_map):
        msgs = []
        game_map = dungeon_map.tiles
        entities = dungeon_map.objects
        # Create a FOV map that has the dimensions of the map
        width = len(game_map)
        height = len(game_map[0])
        fov = libtcod.map_new(width, height)

        # Scan the current map each turn and set all the walls as unwalkable
        for y1 in range(height):
            for x1 in range(width):
                libtcod.map_set_properties(fov, x1, y1, not game_map[x1][y1].block_sight,
                                           not game_map[x1][y1].blocked)

        # Scan all the objects to see if there are objects that must be navigated around
        # Check also that the object isn't self or the target (so that the start and the end points are free)
        # The AI class handles the situation if self is next to the target so it will not use this A* function anyway
        for entity in entities:
            if entity.blocks and entity != self and entity != target:
                # Set the tile as a wall so it must be navigated around
                libtcod.map_set_properties(fov, entity.x, entity.y, True, False)

        # Allocate a A* path
        # The 1.41 is the normal diagonal cost of moving, it can be set as 0.0 if diagonal moves are prohibited
        my_path = libtcod.path_new_using_map(fov, 1.41)

        # Compute the path between self's coordinates and the target's coordinates
        libtcod.path_compute(my_path, self.x, self.y, target.x, target.y)

        # Check if the path exists, and in this case, also the path is shorter than 25 tiles
        # The path size matters if you want the monster to use alternative longer paths (for example through other rooms) if for example the player is in a corridor
        # It makes sense to keep path size relatively low to keep the monsters from running around the map if there's an alternative path really far away
        if not libtcod.path_is_empty(my_path) and libtcod.path_size(my_path) < 25:
            # Find the next coordinates in the computed full path
            x, y = libtcod.path_walk(my_path, True)
            if x or y:
                # Set self's coordinates to the next path tile
                self.x = x
                self.y = y
        else:
            # Keep the old move function as a backup so that if there are no paths (for example another monster blocks a corridor)
            # it will still try to move towards the player (closer to the corridor opening)
            msgs = self.move_towards(target.x, target.y, dungeon_map)

            # Delete the path to free memory
        libtcod.path_delete(my_path)
        return msgs


class Fighter:
    # combat-related properties and methods (monster, player, NPC).
    def __init__(self, hp, defense, power, xp, death_function=default_death, owner=None):
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

    def take_damage(self, damage, death_text="died", killer=None):
        # apply damage if possible
        if damage > 0:
            self.hp -= damage

            # check for death. if there's a death function, call it
            if self.hp <= 0:

                if killer is not None and killer.fighter is not None and killer.xp is not None:  # yield experience
                    killer.fighter.xp += self.xp

                function = self.death_function
                if function is not None:
                    msg = function(self.owner, death_text)
                    self.death_function = None  # you can only die once
                    if msg:
                        return [msg]
        return []

    def heal(self, amount):
        # heal by the given amount, without going over the maximum
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp

    def attack(self, attacker, target):
        # a simple formula for attack damage
        msgs = []
        attack = random.randint(0, attacker.fighter.power)
        defense = random.randint(0, target.fighter.defense)
        damage = attack - defense

        if damage > 0:
            # make the target take some damage
            msgs = [Message(attacker.name.capitalize() + ' attacks ' + target.name + '.', libtcod.yellow)]
            msgs.extend(target.fighter.take_damage(damage, "killed by " + str(attacker)))
            return msgs
        else:
            return [Message(attacker.name.capitalize() + ' attacks ' + target.name + ' but misses.', libtcod.white)]

    @staticmethod
    def mook():
        return Fighter(hp=10, defense=0, power=2, xp=35)


class BasicMonster:
    def take_turn(self, target, fov_map, game_map):
        results = []

        monster = self.owner
        if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):

            if monster.distance_to(target) >= 2:
                results.extend(monster.move_astar(target, game_map))

            elif target.fighter.hp > 0:
                attack_results = monster.fighter.attack(monster, target)
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
             MT("satyr", 'h', libtcod.darkest_crimson),
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
             MT("Sue the T-Rex", 'D', libtcod.dark_yellow),
             MT("Professor Oak", 'O', libtcod.white)
             ]


def make_enemy(x, y, floor):
    template = random_choice_index(templates)
    fighter_component = Fighter(hp=10, defense=0, power=2, xp=35)
    ai_component = BasicMonster()
    enemy = Character(x, y, fighter=fighter_component, *template.to_args(), ai=ai_component)
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


def get_blocking_entities_at_location(entities, destination_x, destination_y):
    for entity in entities:
        if entity.blocks and entity.x == destination_x and entity.y == destination_y:
            return entity

    return None
