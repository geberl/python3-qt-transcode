#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
import os


def unify(default_settings, user_settings):
    """ Compare the default settings with the user settings

    The following logic is being applied:
    - If the setting the user specified actually exists in the defaults then use whatever the user specified.
    - If it doesn't exist just ignore it.
    - If the user didn't specify a setting then use the default.
    - If the type of the user setting is different than the type of the default setting use the default.

    Limitations:
    - No range checks are performed on the user settings yet.
    - No "if value in ['a', 'b']" checks are performed on the user settings yet.

    :param default_settings: dict
    :param user_settings: dict
    :return: dict
    """
    unified_settings = {}

    for key, value in default_settings.items():
        if key in user_settings:
            if type(value) is dict:
                new_val = unify(default_settings[key], user_settings[key])
            else:
                if isinstance(user_settings[key], type(value)):
                    new_val = user_settings[key]
                else:
                    new_val = default_settings[key]
            unified_settings[key] = new_val
        else:
            unified_settings[key] = default_settings[key]

    return unified_settings


def compress(default_settings, current_settings):
    """ Write all non-defaults to a new file if there are non-default settings present.

    Useful to remove all user settings that failed the type check before saving.
    Useful to have all users that were on the defaults use the new defaults if they change due to an update.

    :param default_settings: dict
    :param current_settings: dict
    :return: dict
    """
    compressed_settings = {}

    for key, value in default_settings.items():
        if type(value) is dict:
            new_val = compress(value, current_settings[key])
            if len(new_val) > 0:
                compressed_settings[key] = new_val
        else:
            if value != current_settings[key]:
                compressed_settings[key] = current_settings[key]

    return compressed_settings


# Specify defaults in code of program, to make it impossible to overwrite them by the user or loose them somehow.
default_s = {
    'size': 1,
    'position': {
        'y': 2,
        'x': 3,
        'z': 4,
        'gamma': {'hue': 21,
                  'a': '45%'}
    },
    'command': 'rm -r'
}


if __name__ == '__main__':
    # Notes on usage & simple example here.

    # Load the user's settings from a json file if this file exists. Otherwise just use the defaults.
    user_s_path = 'settings_user.json'
    if os.path.isfile(user_s_path):
        with open(user_s_path, 'r') as f:
            user_s = json.load(f)

        # Unify the default settings with the user settings.
        settings = unify(default_s, user_s)
    else:
        settings = default_s

    # Access current settings.
    print(settings['size'])
    print(type(settings['size']))
    print(settings['position']['x'])
    print(settings['position']['y'])
    print(settings['command'])

    # Write the complete current settings to a new file.
    complete_s_path = 'settings_current_complete.json'
    with open(complete_s_path, 'w') as f:
        json.dump(settings, f)

    # Write only non-defaults to a new file.
    non_default_s = compress(default_s, settings)
    if len(non_default_s) > 0:
        non_default_s_path = 'settings_current_compressed.json'
        with open(non_default_s_path, 'w') as f:
            json.dump(non_default_s, f)
