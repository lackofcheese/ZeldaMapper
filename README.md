ZeldaMapper
===========
An automated mapper for Zelda and ZeldaC (NES), and possibly other games
of a similar nature. The idea is to generate a map using only what you've
seen so far, thus avoiding any spoilers you'd get by looking one up on the
Internet.

Configuration
-------------
Before using the mapper, you will need to change "folder" in the [Snaps]
section of settings.cfg, which sets the directory to be watched for new
screenshots. This should be the same as your emulator's screenshot output
folder.

Additionally, if you are using an emulator other than FCEUX you will probably
need to change the setting "format" in [Snaps]; if automatic recognition of the
current game is not required, `.*\.png` should work for all emulators.

Usage
-----
To run and use the mapper, simply run mapper.py from a command line; basic usage
instructions are given on startup. The mapper works by monitoring a particular
screenshot folder for new screenshots---the folder to be monitored can be set
by changing the "folder" line in the "Snaps" section of settings.cfg.
In particular, the mapper uses the in-game minimap indicator in each individual
screenshot to work out where that screen fits in the overall world map.

It doesn't matter whether you run the mapper before or after the emulator,
as long as the mapper program is running whenever you actually take a
screenshot in-game. Any screenshots you took while not running mapper.py
will simply be ignored.

Switching between multiple maps for the same game
-------------------------------------------------
While the mapper is running, it cannot automatically recognize the difference
between different maps in the game (e.g. the overworld vs the first dungeon).
In order to make two different maps at once, you should use the command line
to switch between different maps for the same game. For example,
upon entering the first dungeon you could use the command
/dungeon-1
to create a new map called "dungeon-1". Then, when you exit the dungeon,
you would use the command
/overworld
to switch back to the default overworld-mapping behaviour.
