#!/usr/bin/env python2

import ConfigParser
import os
import logging
import argparse

from gmusicapi import Mobileclient
from gmusicapi import Webclient

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

    parser.add_argument('-d', '--dst',help='Use dst credentials instead of src', action='store_true',dest='dst')
    parser.add_argument('-t', '--trackid', help='Store ID for the Track', dest='trackid')

    args = parser.parse_args()

    # do some arg parsing here later

    api = Mobileclient()
    if args.dst:
        api.login(dst_user, dst_pass, dst_device)
    else:
        api.login(src_user, src_pass, src_device)
    
    print api.get_track_info(args.trackid)

if __name__ == '__main__':
    main() 
