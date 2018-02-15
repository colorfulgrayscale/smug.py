#!/usr/bin/env python

# author Tejeshwar Sangam - tejeshwar.s@gmail.com
# https://github.com/colorfulgrayscale/smug

import os, sys, tty, termios, threading, time, optparse, random, platform, difflib
from subprocess import Popen, PIPE
from datetime import timedelta, datetime


if platform.system() != 'Darwin':
    print('This program works only on MacOS X')
    exit()

parser = optparse.OptionParser(usage='%prog [file/folder] --shuffle --recursive', version='0.2', )
parser.add_option(
        '-s', '--shuffle',
        dest='shuffle',
        default=False,
        action='store_true',
        help='Shuffle mode.')
parser.add_option(
        '-r', '--recursive',
        dest='recursive',
        default=False,
        action='store_true',
        help='Find music files recursively')
options, args = parser.parse_args()
ch = '~'
autoplay_next_track = True


class MusicFile:
    def __init__(self, name=None, path=None):
        self.name = name
        self.path = path

    def __str__(self):
        return "%s/%s" % (self.path, self.name)


class Playlist:
    def __init__(self):
        self.playlist = list()
        self.random_history = list()
        self.random_history = -1
        self.supported_files = ['.mp3', '.wav', '.aif', '.m4a']
        self.repeat = False

    def add(self, filename, folder):
        basename, extension = os.path.splitext(filename)
        if extension in self.supported_files:
            self.playlist.append(MusicFile(name=filename, path=folder))

    def add_folder(self, folder):
        if options.recursive:
            for root, subFolders, files in os.walk(folder):
                for filename in files:
                    self.add(filename, root)
        else:
            for filename in os.listdir(folder):
                self.add(filename,folder)

    def add_generic(self, name):
        if os.path.isdir(name):
            self.add_folder(name)
        elif os.path.isfile(name):
            folder, filename = os.path.split(name)
            if not folder:
                folder = os.getcwd()
            self.add(filename, folder)
        else:
            return -1

    def count(self):
        return len(self.playlist)

    def current_song(self):
        return self.playlist[self.random_history]

    def find_song(self, song):
        if song.isdigit() and int(song) <= len(self.playlist):
            self.random_history = int(song) - 1
            return self.playlist[self.random_history]
        search_index = -1
        highest_match_ratio = -1
        threshold_ratio = 0.2
        for (counter, files) in enumerate(self.playlist):
            temp = difflib.SequenceMatcher(None, files.name, song).ratio()
            if (temp > highest_match_ratio) and (temp > threshold_ratio):
                search_index = counter
                highest_match_ratio = temp
        if search_index != -1:
            self.random_history = search_index
            return self.playlist[self.random_history]
        return -1

    def random_song(self):
        self.random_history = random.randrange(len(self.playlist))
        return self.playlist[self.random_history]

    def first_song(self):
        if len(self.playlist) > 0:
            self.random_history = 0
            return self.playlist[0]

    def last_song(self):
        if len(self.playlist) > 0:
            self.random_history = len(self.playlist) - 1
            return self.playlist[-1]

    def next_song(self):
        if self.repeat:
            return self.current_song()
        if options.shuffle:
            song = self.random_song()
            playlist.random_history.append(song)
            return song
        if self.random_history + 1 > len(self.playlist) - 1:
            return self.first_song()
        self.random_history = self.random_history + 1
        return self.playlist[self.random_history]

    def prev_song(self):
        if self.repeat:
            return self.current_song()
        if options.shuffle:
            if len(self.random_history) <= 1:
                return self.random_history[0]
            else:
                song = self.random_history.pop()
                if "%s" % song == "%s" % self.current_song():
                    return self.random_history.pop()
                else:
                    return song
        if self.random_history - 1 < 0:
            return self.last_song()
        self.random_history = self.random_history - 1
        return self.playlist[self.random_history]

    def toggle_repeat(self):
        if self.repeat:
            print("\033[0;31mX. [Single Track Looping Disabled]\033[0m")
            self.repeat = False
        else:
            print("\033[0;31mX. [Single Track Looping Enabled]\033[0m")
            self.repeat = True

    def __str__(self):
        print("\033[0;32m\nPlaylist had %d file(s)"%len(self.playlist))
        print('-'*50)
        print("\033[0m",)
        for (counter, files) in enumerate(self.playlist):
            if counter == self.random_history:
                print("\033[0;31m-> %d. %s \033[0m" % (counter + 1, files.name))
            else:
                print("%d. %s "%(counter + 1, files.name))
        print("\033[0;32m",)
        print('-'*50)
        print("\033[0m",)
        return ""


playlist = Playlist()


class Player:
    def __init__(self):
        self.is_playing = False
        self.player_pid = -1
        self.player = -1
        self.play_counter = 0
        self.current_song = ''
        self.current_path = ''

    def get_duration(self, music_file):
        try:
            raw = Popen('afinfo "{}"'.format(music_file), shell=True, stdout=PIPE).stdout.readlines()
            out = str([l for l in raw if b'estimated duration:' in l][0]).split()[2]
            sec = timedelta(seconds=int(float(out)))
            duration = datetime(1, 1, 1) + sec
            return "{}:{}".format(duration.minute, duration.second)
        except Exception as e:
            print(e)
            return ""

    def play(self, music_file):
        if ch == 'q':
            return
        self.play_counter = self.play_counter + 1
        self.stop()
        self.is_playing = True
        self.player = Popen('afplay "%s" -q 1' % music_file, shell=True)
        self.player_pid = self.player.pid
        self.current_song = "\r%d. %s - \033[1m%s mins\033[0m" % (self.play_counter,
                                                                  music_file.name,
                                                                  self.get_duration(music_file))
        self.current_path = '{}'.format(str(music_file))
        if playlist.repeat:
            self.current_song = "%s %s" % (self.current_song, "[Looping]%20s\r" % '')
        else:
            self.current_song = "%s %s" % (self.current_song, "%20s\r" % '')
        print(self.current_song)

    def stop(self):
        if self.player_pid == -1 or self.is_playing == False:
            return
        self.is_playing = False
        try:
            self.player.kill()
        except:
            pass

    def pause(self):
        if self.player_pid == -1 or self.is_playing == False:
            return
        print("\033[0;31m\r  [Muted]%20s\r\033[0m" % '', )
        Popen("kill -STOP %d " % self.player_pid, shell=True)
        self.is_playing = False

    def resume(self):
        if self.player_pid == -1 or self.is_playing == True:
            return
        print("\r%20s\r" % '',)
        Popen("kill -CONT %d" % self.player_pid, shell=True)
        self.is_playing = True

    def toggle_play_pause(self):
        if self.is_playing:
            self.pause()
        else:
            self.resume()

    def track_finished(self):
        try:
            a = self.player.poll()
        except:
            return False
        if a == 0:
            return True
        else:
            return False


player = Player()


class PlayerThread(threading.Thread):
    def run(self):
        global ch
        if len(args) > 0:
            sucess = playlist.add_generic(args[0])
            if sucess == -1:
                print("%s not found!" % args[0])
                exit()
        else:
            playlist.add_folder(os.getcwd())
        print("Found %d music file(s).\n\033[0m" % playlist.count())
        if playlist.count() <= 0:
            ch = 'q'
            exit()
        UpdaterThread().start()
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        while ch != 'q':
            try:
                tty.setraw(sys.stdin.fileno())
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            player_controls()


class UpdaterThread(threading.Thread):
    def run(self):
        player.play(playlist.next_song())
        global ch, autoplay_next_track
        while ch != 'q':
            try:
                time.sleep(1)
            except:
                pass
            if player.track_finished() and autoplay_next_track:
                player.play(playlist.next_song())


def player_controls():
    global ch, autoplay_next_track
    if ch == 'n' or ch == 'j':
        player.play(playlist.next_song())
    elif ch == 'p' or ch == 'k':
        player.play(playlist.prev_song())
    elif ch == 'r':
        player.play(playlist.current_song())
    elif ch == 's':
        player.play(playlist.random_song())
    elif ch == 'l':
        playlist.toggle_repeat()
    elif ch == 'i':
        print("%s\n%s" % (playlist, player.current_song))
    elif ch == 'm':
        print('{}'.format(player.current_path))
    elif ch == 't':
        notes_file_path = os.path.expanduser('~/Music/smug_notes.txt')
        with open(notes_file_path, '+a') as notes_file:
            notes_file.write('{}\t{}\n'.format(time.strftime('%Y-%m-%d-%H:%M:%S'), player.current_path))
        print('note: {} >> {}'.format(time.strftime('%Y-%m-%d-%H:%M:%S'), player.current_path))
    elif ch == '/':
        autoplay_next_track = False
        print("\033[0;31m\r%30s\r" % '', )
        foo = input("X. Jump to song: ")
        song = playlist.find_song(foo)
        if song == -1:
            print("\r  [Song Not Found!]%20s\r" % '', )
            print("\033[0m",)
        else:
            print("\033[0m",)
            player.play(song)
        autoplay_next_track = True
    elif ch == 'q':
        print("\033[0;31m\nQuiting...\033[0m")
        player.stop()
        exit()
    elif ch == ' ':
        player.toggle_play_pause()


if __name__ == '__main__':
    print("Searching for music files")
    PlayerThread().start()
