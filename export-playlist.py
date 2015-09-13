#!/usr/bin/env python2

import logging
import argparse
import time
import os
import ConfigParser

from gmusicapi import Mobileclient
from gmusicapi import Webclient
from gmusicapi import exceptions

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('gmusic-sync')

def main():
    log.setLevel(logging.INFO)
    logging.getLogger('gmusicapi').setLevel(logging.INFO)
    
    cred_path = os.path.join(os.path.expanduser('~'), '.gmusic-sync')

    if not os.path.isfile(cred_path):
        raise NoCredentialException(
                    'No username/password was specified. No config file could '
                    'be found either. Try creating %s and specifying your '
                    'username/password there. Make sure to chmod 600.'
                    % cred_path)
    if not oct(os.stat(cred_path)[os.path.stat.ST_MODE]).endswith('00'):
        raise NoCredentialException(
                    'Config file is not protected. Please run: '
                    'chmod 600 %s' % cred_path)
    
    config = ConfigParser.ConfigParser()
    config.read(cred_path)

    src_user = config.get('src','username')
    src_pass = config.get('src','password')
    src_device = config.get('src','deviceid')

    dst_user = config.get('dst','username')
    dst_pass = config.get('dst','password')
    dst_device = config.get('dst','deviceid')

    if not src_user or not src_pass or not dst_user or not dst_pass:
        raise NoCredentialException(
                    'No username/password could be read from config file'
                    ': %s' % cred_path)
    if not src_device or not dst_device:
         raise NoCredentialException(
                    'No deviceId could be read from config file'
                    ': %s' % cred_path)

    parser = argparse.ArgumentParser(description='gmusic-sync', add_help=False)

    parser.add_argument('-h', '--heuristics', help='Use heuristics to try and find missing songs. Songs must match artist and title to be considered a match.', action='store_true', dest='heuristics')
    parser.add_argument('-hs', '--strict-heuristics', help='Songs must match artist, album, and title to be considered a match.', action='store_true', dest='strict_heuristics')
    parser.add_argument('-l', '--list', help='List playlists on the src account', action='store_true', dest='lst')
    parser.add_argument('-p', '--playlist', help='Playlist ID from src account to transfer', dest='playlist')
    args = parser.parse_args()

    api = Mobileclient()
    api.login(src_user, src_pass, src_device)

    playlists = api.get_all_playlists()

    if args.lst:
        for playlist in playlists:
            print playlist['name'] + ' (' + playlist['id'] + ') '
        exit()

    library = api.get_all_songs()

    api2 = Mobileclient()
    api2.login(dst_user, dst_pass, dst_device)
    library2 = api2.get_all_songs()

    if args.playlist is None:
        print 'Error: no playlist selected'

    all_playlist_entries = api.get_all_user_playlist_contents()

    selected_playlist_entries = []
    dst_playlist_id = None
    
    for entry in all_playlist_entries:
        if entry['id'] == args.playlist:
            selected_playlist_entries = entry['tracks']
            dst_playlist_id = api2.create_playlist(entry['name'])

    if dst_playlist_id is None:
        print 'Error creating new playlist'
        exit()

    playlist_tracks = []

    for ptrack in selected_playlist_entries:
        for track in library:
            if ptrack['trackId'] == track['id']:
                playlist_tracks.append(track)

    if len(playlist_tracks) != len(selected_playlist_entries):
        print 'Error: could not locate all playlist tracks in src library'
        exit()
    
    failed_tracks = []

    for track in playlist_tracks:
        try:
            if track['storeId'].startswith('T'):
                #It's a store track: does it exist in the target store?
                #Perform a store lookup: this will raise an exception if the track
                #Is not in the target store
                store_track = api2.get_track_info(track['storeId'])
                #If we got here, we're good to go for adding the track to the playlist
                retval = api2.add_songs_to_playlist(dst_playlist_id, track['storeId'])
                if track['storeId'] not in retval:
                    print 'Error adding   '  + track['title'] + ' - ' + track['artist'] + ' (' + track['album'] + ')'
            else:
                dst_track = heuristic_search(library2, track, args.strict_heuristics)
                if dst_track is not None:
                    api2.add_songs_to_playlist(dst_playlist_id, dst_track['id'])
                else:
                    failed_tracks.append(track)
        except:
            #Not a store track: do heuristics lookup
            dst_track = heuristic_search(library2, track, args.strict_heuristics)
            if dst_track is not None:
                api2.add_songs_to_playlist(dst_playlist_id, dst_track['id'])
            else:
                failed_tracks.append(track)

            continue

    print '----------------- FAILED TRACKS --------------------'
    for track in failed_tracks:
        print track['title'] + ' - ' + track['artist'] + ' (' + track['album'] + ')'

def heuristic_search(library, track, strict):
    print 'Heuristics Search Start for   ' + track['title'] + ' - ' + track['artist'] + ' (' + track['album'] + ')'
    try: 
        for test_track in library:
            if strict:
                if test_track['album'] == track['album'] and test_track['title'] == track['title'] and test_track['artist'] == track['artist']:
                    print 'Strict Heuristic Match!  ' + test_track['title'] + ' - ' + test_track['artist'] + ' (' + test_track['album'] + ')'
                    return test_track
            else:
                if test_track['title'] == track['title'] and test_track['artist'] == track['artist']:
                    print 'Weak Heuristic Match!  ' + test_track['title'] + ' - ' + test_track['artist'] + ' (' + test_track['album'] + ')'
                    return test_track 
    except:
        print 'Error occured performing heuristic search. Assuming track is not already in library'

    return None

if __name__ == '__main__':
    main() 
