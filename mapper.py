#!/usr/bin/env python
import os, time, sys, re, subprocess
import ConfigParser
import threading
import Image

HELP_STRING = """\
Automated Zelda mapper!
Take screenshots in-game and the map will automatically be updated with that
screen. Switch to mapping a dungeon using a command like "/level-1", or
map grottos using "/grottos".

Commands:
exit - quit the mapper
[game]/[loc] - change game and/or location (leave one blank to change only
               the other, e.g. "ZeldaC/")
show - re-display the current map
clean - delete all files in the screenshot folder
reset - reset the current map"""

# From stackoverflow 434597
def open_file(filepath):
    """ Opens a file using the default application for that file type.
    This is used to open a viewer for the map file."""
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', filepath))
    elif os.name == 'nt':
        os.startfile(filepath)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', filepath))

class Mapper(object):
    """ Converts in-game screenshots into tiled maps and manages the
    map data."""
    
    def __init__(self, maps_folder, display_file, game, loc):
        """ Creates a mapper with the given folder and display file that
        starts off mapping the given game and location. """
        self._maps_folder = maps_folder
        self._display_map_path = display_file
        self.set_game_loc(game, loc)

    def process(self, snap):
        """ Processes a screenshot to get the tile and its location, and adds
        it to the map."""
        if snap.size != (self._screen_width, self._screen_height):
            sys.stderr.write('Wrong screenshot size!\n')
            return
        data = snap.load()
        coords = None
        for i in xrange(self._num_hori):
            for j in xrange(self._num_vert):
                if self.has_character_at(data, (i, j)):
                    coords = (i, j)
                    break
            if coords is not None:
                break
        if coords is None:
            sys.stderr.write('Could not find location from screenshot.\n')
            return None
        tile = snap.crop((self._tile_left, self._tile_top,
            self._tile_left + self._tile_width,
            self._tile_top + self._tile_height))
        filename = '{}-{}.png'.format(*coords)
        tile.save(os.path.join(self._folder, filename))
        self.update_tile(coords, tile)
        self.save_map()

    def show(self):
        """ Uses an external application to display the current map. """
        open_file(self._display_map_path)
        
    def update_tile(self, (i, j), im):
        """ Updates a given tile in the current map. """
        self._map.paste(im, (i * self._tile_width, j * self._tile_height))

    def clear_map(self):
        """ Clears the current map. """
        self._map = Image.new('RGBA', (self._num_hori * self._tile_width,
            self._num_vert * self._tile_height), (0, 0, 0, 0))

    def reset_map(self):
        """ Resets the current map, removing any saved tiles. """
        self.clear_map()
        for name in os.listdir(self._folder):
            os.remove(os.path.join(self._folder, name))
        self.save_map()

    def load_tile(self, path):
        """ Loads a single tile from a file with the given path.
        The filename must be (column)-(row).png """
        name = os.path.split(path)[1]
        m = re.match('^([0-9]+)-([0-9]+)\.png$', name)
        if m is not None:
            coords = tuple(int(g) for g in m.groups())
            self.update_tile(coords, Image.open(path))

    def remake_map(self):
        """ Reloads the map using the saved tiles. """
        self.clear_map()
        names = os.listdir(self._folder)
        for name in names:
            self.load_tile(os.path.join(self._folder, name))
        if self._loc == 'grottos':
            names = set(names)
            folder = os.path.join(self._maps_folder, self._game, 'overworld')
            for name in os.listdir(folder):
                if name not in names:
                    self.load_tile(os.path.join(folder, name))
        self.save_map()

    def save_map(self):
        """ Saves the current map, and updates the current display file."""
        self._map.save(self._map_path)
        self._map.save(self._display_map_path)

    def set_game_loc(self, game, loc):
        """ Changes the location and game currently being mapped.
        To change only one value, input an empty string for the other. """
        if game:
            self._game = game
        if loc:
            self._loc = loc
        self._folder = os.path.join(self._maps_folder, self._game, self._loc)
        if not os.path.isdir(self._folder):
            os.makedirs(self._folder)
        self._map_path = os.path.join(self._maps_folder, self._game,
                                      self._loc + '.png')
        self.load_settings()
        self.remake_map()

    def load_settings(self):
        """ Loads the settings for the current game. """
        settings = ConfigParser.RawConfigParser()
        settings.read(['game-defaults.cfg', 
            os.path.join('game-settings', self._game)])
        self._screen_width = settings.getint('Screen', 'width')
        self._screen_height = settings.getint('Screen', 'height')
        self._tile_width = settings.getint('Tile', 'width')
        self._tile_height = settings.getint('Tile', 'height')
        self._tile_left = settings.getint('Tile', 'left')
        self._tile_top = settings.getint('Tile', 'top')
        if not settings.has_section(self._loc):
            settings.add_section(self._loc)
        self._num_hori = settings.getint(self._loc, 'num_hori')
        self._num_vert = settings.getint(self._loc, 'num_vert')
        self._x0 = settings.getint(self._loc, 'x0')
        self._y0 = settings.getint(self._loc, 'y0')
        self._dx = settings.getint(self._loc, 'dx')
        self._dy = settings.getint(self._loc, 'dy')
        self._colors = [int(c) for c in 
                settings.get(self._loc, 'colors').split(',')]

    def has_character_at(self, data, (i, j)):
        """ Checks if the minimap in the frame data matches
        tile co-ordinates (i,j). """
        return data[self._x0+i*self._dx, self._y0+j*self._dy] in self._colors

def watch_folder(period, folder, fmt, mapper,
        mapper_lock, clean_event, exit_event):
    """ A thread to continuously watch the screenshot folder
    for new screenshots; checks with the given period (in seconds)
    until it detects that exit_event is set. """
    # Load the list of files to be ignored (usually ones that have already
    # been processed).
    ignores = set()
    if os.path.isfile('ignores.txt'):
        with open('ignores.txt', 'rU') as f:
            for line in f:
                line = line.strip()
                if line:
                    ignores.add(line.strip())
    # Start the update loop.
    while True:
        clean = clean_event.is_set()
        for name in os.listdir(folder):
            filepath = os.path.join(folder, name)
            if name not in ignores:
                m = re.match(fmt, name)
                if m is None:
                    sys.stderr.write('Invalid filename {} - '
                            'must match {}\n'.format(name, fmt))
                else:
                    try:
                        game = m.group('game')
                    except IndexError:
                        game = ''
                    with mapper_lock:
                        mapper.set_game_loc(game, '')
                        mapper.process(Image.open(filepath))
                ignores.add(name)
                if not clean:
                    with open('ignores.txt', 'a') as f:
                        f.write(name + '\n')
            if clean:
                os.remove(filepath)
        if clean:
            ignores.clear()
            open('ignores.txt', 'w').close()
            clean_event.clear()
        if exit_event.wait(period):
            break

if __name__ == '__main__':
    settings = ConfigParser.SafeConfigParser()
    settings.read('settings.cfg')
    mapper = Mapper(os.path.expanduser(settings.get('Maps', 'folder')),
            os.path.expanduser(settings.get('Maps', 'display_file')),
            settings.get('Startup', 'game'),
            settings.get('Startup', 'location'))
    mapper.show()
    mapper_lock = threading.Lock()
    clean_event = threading.Event()
    exit_event = threading.Event()
    update_thread = threading.Thread(target=watch_folder,
            args=(1.0,
                os.path.expanduser(settings.get('Snaps', 'folder')),
                settings.get('Snaps', 'format'),
                mapper, mapper_lock, clean_event, exit_event))

    print HELP_STRING
    print
    update_thread.start()
    # Command line I/O loop
    while True:
        line = raw_input('>>> ')
        if len(line.split()) == 1:
            line = line.strip()
            if line == 'exit':
                exit_event.set()
                update_thread.join()
                sys.exit(0)
            elif line == 'show':
                with mapper_lock:
                    mapper.show()
            elif line == 'reset':
                with mapper_lock:
                    mapper.reset_map()
            elif line == 'clean':
                clean_event.set()
            elif '/' in line:
                tokens = line.split('/')
                if len(tokens) == 1:
                    tokens.append('')
                if len(tokens) == 2:
                    with mapper_lock:
                        mapper.set_game_loc(*tokens)
