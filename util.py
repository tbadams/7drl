import tcod as libtcod
from collections import namedtuple
import json
import random


def random_choice_index(chances):  # choose one option from list of chances, returning its index
    # the dice will land on some number between 1 and the sum of the chances
    # dice = libtcod.random_get_int(None, 1, sum(chances))
    return chances[random.randint(0, len(chances) -1)]


def random_choice(chances_dict):
    # choose one option from dictionary of chances, returning its key
    chances = chances_dict.values()
    strings = chances_dict.keys()

    return strings[random_choice_index(chances)]


# https://stackoverflow.com/questions/6578986/how-to-convert-json-data-into-a-python-object
def _json_object_hook(d): return namedtuple('X', d.keys())(*d.values())


def json2obj(data): return json.loads(data, object_hook=_json_object_hook)


def pad(text, desired_length):
    while len(text) < desired_length:
        text += " "
    return text
