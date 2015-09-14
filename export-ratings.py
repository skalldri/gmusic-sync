#!/usr/bin/env python2

import logging
import argparse
import time
import os
import ConfigParser
import operator

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

    parser.add_argument('-hs', '--strict-heuristics', help='Songs must match artist, album, and title to be considered a match.', action='store_true', dest='strict_heuristics')
    parser.add_argument('-e', '--exact', help='Copy the exact rating, instead of upgrading from 1-5 star ratings to Thumbs Up/Down', action='store_true', dest='exact')
    args = parser.parse_args()

    api = Mobileclient()
    api.login(src_user, src_pass, src_device)
    library = api.get_all_songs()

    api2 = Mobileclient()
    api2.login(dst_user, dst_pass, dst_device)
    library2 = api2.get_all_songs()

    failed_tracks = []
    rated_tracks = []

    #first, get all tracks in the library with a rating
    for track in library:
        try:
            if track['rating'] != '0' and track['lastRatingChangeTimestamp'] != '0':
                rated_tracks.append(track)
        except:
            #print 'ERROR: track did not contain rating key: ' + track_info_str(track)
            pass

    #sort the tracks by rating date
    rated_tracks.sort(key=operator.itemgetter('lastRatingChangeTimestamp'))

    for track in rated_tracks:
        print track_info_str(track)

    print 'TOTAL RATED TRACKS: ' + str(len(rated_tracks))

    for track in rated_tracks:
        try:
            if track['storeId'].startswith('T'):
                #It's a store track: does it exist in the target store?
                #Perform a store lookup: this will raise an exception if the track
                #Is not in the target store
                dst_track = api2.get_track_info(track['storeId'])
                #If we got here, the song is ready to be rated
                transfer_rating(api2, track, dst_track, args.exact)

            else:
                dst_track = heuristic_search(library2, track, args.strict_heuristics)
                if dst_track is not None:
                    transfer_rating(api2, track, dst_track, args.exact)
                else:
                    failed_tracks.append(track)
        except:
            #Not a store track: do heuristics lookup
            dst_track = heuristic_search(library2, track, args.strict_heuristics)
            if dst_track is not None:
                transfer_rating(api2, track, dst_track, args.exact)
            else:
                failed_tracks.append(track)
        #Absolutely must wait between ratings or we won't get valid timestamps
        time.sleep(2)

    print '----------------- FAILED TRACKS --------------------'
    for track in failed_tracks:
        print track_info_str(track)

def track_info_str(track):
    base_str = track['title'] + ' - ' + track['artist'] + ' (' + track['album'] + ')'
    try:
        if track['rating'] != '0':
            base_str += ' RATING: ' + track['rating']
    except:
        pass

    return base_str

def transfer_rating(api2, src_track, dst_track, exact):
    if exact:
        dst_track['rating'] = src_track['rating']
        res = api2.change_song_metadata(dst_track)
    else:
        if int(src_track['rating']) >= 3:
            dst_track['rating'] = '5'
        else:
            dst_track['rating'] = '1'
        res = api2.change_song_metadata(dst_track)

    if len(res) != 1:
        raise Exception('Could not change track metadata!')


def heuristic_search(library, track, strict):
    print 'Heuristics Search Start for   ' + track_info_str(track)
    try: 
        for test_track in library:
            if strict:
                if test_track['album'] == track['album'] and test_track['title'] == track['title'] and test_track['artist'] == track['artist']:
                    print 'Strict Heuristic Match!  ' + track_info_str(test_track)
                    return test_track
            else:
                if test_track['title'] == track['title'] and test_track['artist'] == track['artist']:
                    print 'Weak Heuristic Match!  ' + track_info_str(test_track) 
                    return test_track 
    except:
        print 'Error occured performing heuristic search. Assuming track is not already in library'

    return None

if __name__ == '__main__':
    main() 
