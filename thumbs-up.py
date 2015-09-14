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

    parser.add_argument('-d', '--dst', help='Perform operation on the dst account', action='store_true', dest='dst')
    parser.add_argument('-l', '--list', help='List playlists on the src account', action='store_true', dest='lst')
    parser.add_argument('-p', '--playlist', help='Playlist ID from src account to transfer', dest='playlist')
    args = parser.parse_args()

    api = Mobileclient()
    if args.dst:
        api.login(dst_user, dst_pass, dst_device)    
    else:
        api.login(src_user, src_pass, src_device)

    playlists = api.get_all_playlists()

    if args.lst:
        for playlist in playlists:
            print playlist['name'] + ' (' + playlist['id'] + ') '
        exit()

    library = api.get_all_songs()

    if args.playlist is None:
        print 'Error: no playlist selected'

    all_playlist_entries = api.get_all_user_playlist_contents()

    selected_playlist_entries = []
    
    for entry in all_playlist_entries:
        if entry['id'] == args.playlist:
            selected_playlist_entries = entry['tracks']

    playlist_tracks = []

    for ptrack in selected_playlist_entries:
        track_found = False
        for track in library:
            if ptrack['trackId'] == track['id']:
                playlist_tracks.append(track)
                track_found = True
                break
            try:
                if ptrack['trackId'] == track['storeId']:
                    playlist_tracks.append(track)
                    track_found = True
                    break
            except:
                pass
        if not track_found:
            print 'ERROR: could not find playlist entry ' + str(ptrack)
            api.add_aa_track(ptrack['trackId'])

    if len(playlist_tracks) != len(selected_playlist_entries):
        print 'Error: could not locate all playlist tracks in src library'
        exit()
    
    failed_tracks = []

    playlist_tracks_reversed = []

    for track in playlist_tracks:
        playlist_tracks_reversed.insert(0, track)

    for track in playlist_tracks_reversed:
        track['rating'] = '5'
        res = api.change_song_metadata(track)

        if len(res) != 1:
            raise Exception('Could not change track metadata!')

        time.sleep(1)

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
