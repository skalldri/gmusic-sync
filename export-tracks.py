#!/usr/bin/env python2

import logging
import argparse
import time
import os
import ConfigParser

from gmusicapi import Mobileclient
from gmusicapi import Webclient
from gmusicapi import exceptions

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('gmusic-sync')

def main():
    log.setLevel(logging.DEBUG)
    logging.getLogger('gmusicapi').setLevel(logging.DEBUG)
    
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

    parser.add_argument('-a', '--add-songs', help='Add songs from the src account to the dst account', action='store_true', dest='add')
    parser.add_argument('-h', '--heuristics', help='Use heuristics to try and find missing songs. Songs must match artist and title to be considered a match.', action='store_true', dest='heuristics')
    parser.add_argument('-hs', '--strict-heuristics', help='Songs must match artist, album, and title to be considered a match.', action='store_true', dest='strict_heuristics')
    args = parser.parse_args()

    api = Mobileclient()
    api.login(src_user, src_pass, src_device)
    library = api.get_all_songs()

    api2 = Mobileclient()
    api2.login(dst_user, dst_pass, dst_device)
    library2 = api2.get_all_songs()

    aa_songs2 = []
    aa_diff = []
    
    for track in library2:
        try:
            if track['storeId'].startswith('T'):
                aa_songs2.append(track['storeId'])
        except KeyError:
            continue

    for track in library:
        try:
            if track['storeId'].startswith('T') :
                if track['storeId'] not in aa_songs2:
                    aa_diff.append(track)
                    if args.add:
                        api2.add_aa_track(track['storeId'])
                        time.sleep(5) # sleep so Google doesn't banhammer you for spamming their servers
        except KeyError:
            continue
        except:
            #Track wasn't found in the dst database. See if we can match to an existing song or something
            #else from the store
            #if args.heuristics:
                #Anything in the dst library already?
            #    track_details = api.get_track_info(track['storeId'])
            #    for track in library2:
            #        if args.strict_heuristics:
            #            
            #        else:
                                    
            print 'ERROR ADDING: ' + track['title'] + ' - ' + track['artist'] + ' (' + track['album'] + ')' + ' (' + track['storeId'] + ')'
            continue

    print '----------------- TRACKS NOT IN DST --------------------'
    for track in aa_diff:
        print track['title'] + ' - ' + track['artist'] + ' (' + track['album'] + ')'

if __name__ == '__main__':
    main() 
