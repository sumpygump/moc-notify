#!/usr/bin/env python

import dbus
import gobject
import logging
import re
import subprocess
import sys
from dbus.mainloop.glib import DBusGMainLoop

INFO_RE = re.compile(r'^([a-zA-Z]+):\s*(.+)$')

# The path to this application's directory.
APPLICATION_DIR = sys.path[0] + "/"

class MocNotify():
    prevTrack = None
    newTrack = None
    notifyid = 0

    def __init__(self, logger):
        self.log = logger
        self.notifyid  = 0

        self.bus = dbus.Bus(dbus.Bus.TYPE_SESSION)

    def pollChange(self):
        self.newTrack, state = self.getMocInfo()

        #self.log.info('{0} {1}'.format(state, self.newTrack))

        if (state == 'play' and (self.newTrack != self.prevTrack)):
            self.trackChange(self.newTrack)
            self.prevTrack = self.newTrack

        if (state == 'pause' or state == 'stop'):
            self.prevTrack = None

        return True

    def trackChange(self, track):
        self.log.info(track)

        # Connect to notification interface on DBUS.
        self.notifyservice = self.bus.get_object(
            'org.freedesktop.Notifications',
            '/org/freedesktop/Notifications'
        )
        self.notifyservice = dbus.Interface(
            self.notifyservice,
            "org.freedesktop.Notifications"
        )

        coverImage = APPLICATION_DIR + 'icon-moc.png'

        notifyText = "{0}\n{1}".format(
            track.artist,
            track.album
        )

        # The second param is the replace id, so get the notify id back,
        # store it, and send it as the replacement on the next call.
        self.notifyid = self.notifyservice.Notify(
            "moc-notify",
            self.notifyid,
            coverImage,
            track.title,
            notifyText,
            [],
            {},
            5000
        )

    def getMocInfo(self):
        info = {}

        try:
            p = subprocess.Popen('mocp -i', shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
        except:
            return (None, 'stop')

        pstdout, _ = p.communicate()
        pstdout = pstdout.decode('utf8', 'replace') # mocp -i output doesn't depend on locale

        for line in pstdout.splitlines():
            m = INFO_RE.match(line)
            if m:
                key, value = m.groups()
                if value:
                    info[key.lower()] = value.strip()

        artist = info.get('artist', '')
        title = info.get('songtitle', '')
        album = info.get('album', '')
        position = info.get('currentsec', 0)
        length = info.get('totalsec', 0)
        
        state = 'stop'
        if 'state' in info:
            state = info['state'].lower()
        return (Track(artist, title, album, position, length), state)

def setupLogger():
    level = logging.DEBUG

    log = logging.getLogger('moc.notify')
    log.setLevel(level)

    # Create console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)

    # create formatter
    cFormatString = '>> %(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(cFormatString)

    # add formatter to ch
    ch.setFormatter(formatter)

    log.addHandler(ch)

    return log

class Track(object):
    def __init__(self, artist, title, album, position=0, length=0):
        self.artist = artist.strip() if artist else ''
        self.title = title.strip() if title else ''
        self.album = album.strip() if album else ''
        self.length = int(length)
        self.position = int(position)

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__) and
            self.artist.lower() == other.artist.lower() and
            self.title.lower() == other.title.lower()
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __bool__(self):
        if self.artist and self.title: # and self.length:
            return True
        return False

    def __str__(self):
        if self:
            if self.album:
                return '%s - %s (%s)' % (self.artist, self.title, self.album)
            else:
                return '%s - %s' % (self.title, self.artist)
        else:
            return 'None'

    def __repr__(self):
        return '<Track: %s>' % self

def main():
    log = setupLogger()

    print("Moc-notify v0.1")

    DBusGMainLoop(set_as_default=True)
    notifier = MocNotify(log)
    loop = gobject.MainLoop()

    gobject.timeout_add(500, notifier.pollChange)
    loop.run()

    return 0

if __name__ == '__main__':
    sys.exit(main() or 0)
