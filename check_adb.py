#!/usr/bin/python

import sys
import pprint
import re
import subprocess
import urllib
import tempfile
import os
import StringIO
import argparse
import BaseHTTPServer
import time
import json

# http://code.activestate.com/recipes/325905/
class MWT(object):
    """Memoize With Timeout"""
    _caches = {}
    _timeouts = {}
    
    def __init__(self,timeout=2):
        self.timeout = timeout
        
    def collect(self):
        """Clear cache of results which have timed out"""
        for func in self._caches:
            cache = {}
            for key in self._caches[func]:
                if (time.time() - self._caches[func][key][1]) < self._timeouts[func]:
                    cache[key] = self._caches[func][key]
            self._caches[func] = cache
    
    def __call__(self, f):
        self.cache = self._caches[f] = {}
        self._timeouts[f] = self.timeout
        
        def func(*args, **kwargs):
            kw = kwargs.items()
            kw.sort()
            key = (args, tuple(kw))
            try:
                v = self.cache[key]
                print "cache"
                if (time.time() - v[1]) > self.timeout:
                    raise KeyError
            except KeyError:
                print "new"
                v = self.cache[key] = f(*args,**kwargs),time.time()
            return v[0]
        func.func_name = f.func_name
        
        return func

def get_phones(readable):
    devices=[]
    lines_in_block = 0
    current_device={}

    for line in readable.readlines()[2:]:
        line = line.strip(' \t\n\r')

        if len(line) == 0:
            if lines_in_block != 1:
                devices.append(current_device)
                current_device={}
            lines_in_block = 0

        else:
            lines_in_block += 1
            parts = line.rpartition(':')

            if len(parts[2]):
                current_device[parts[0]] = parts[2]

            elif lines_in_block == 1:
                current_device['Name'] = parts[0]
    
            else:
                raise "woops: " + line

    if current_device:
        devices.append(current_device)

    phones = filter(lambda x: 'Serial Number' in x and not '0x05ac' in x['Vendor ID'], devices)
    
    
    vendors = (re.search(r'^\s+0x(\w{4}).*', p['Vendor ID']).group(1) for p in phones)
    products = (re.search(r'^\s+0x(\w{4}).*', p['Product ID']).group(1) for p in phones)
    serials = (p['Serial Number'].strip(' \t\n\r') for p in phones)
    names = (p['Name'] for p in phones)

    return zip(vendors, products, serials, names)


def get_usb_ids(readable):
    
    usb_ids = {}
    for line in readable.readlines():
        if len(line.strip(' \t\n\r')) == 0 or line[0] == '#':
            continue
        
        if line[1] == '\t':
            # interface, ignore
            continue

        elif line[0] == '\t':
            device_id = line[1:5]
            device_name = line[7:-1]
            
            usb_ids[vendor_id + device_id] = vendor_name + ' ' + device_name
            
        else:
            vendor_id = line[:4]
            vendor_name = line[6:-1]
            usb_ids[vendor_id] = vendor_name
    
    return usb_ids

def resolve_devices(phones, usb_ids):
    resolved={}
    for phone in phones:
        key = phone[0] + phone[1]
        try:
            desc = usb_ids[key]
        except KeyError, e:
            desc = usb_ids[phone[0]]
        
        resolved[phone[2]] = (phone[2], phone[0], phone[1], desc, phone[3])
    return resolved

def parse_adb_devices(readable):
    devices = []
    for line in readable.readlines()[1:]:
        line = line.strip(' \t\n\r')
        if len(line) == 0:
            continue
        
        (device, _, status) = line.partition('\t')
            
        devices.append(device)
    return devices

def find_missing(resolved, adb_devices):
    missing = []
    for serial in resolved.keys():
        if not serial in adb_devices:
            missing.append(resolved[serial])
    return missing

def download_usb_ids():
    tempdir = tempfile.gettempdir()
    fname = os.path.join(tempdir, 'usb.ids')
    
    if not os.path.exists(fname):
        urllib.urlretrieve('http://www.linux-usb.org/usb.ids', fname)
    
    return fname

@MWT(timeout=5)
def do_check():
    print >> sys.stderr, "checking"
    phones = get_phones(StringIO.StringIO(subprocess.check_output(['/usr/sbin/system_profiler', 'SPUSBDataType'])))
    usb_ids = get_usb_ids(open(download_usb_ids(), 'r'))
    resolved = resolve_devices(phones, usb_ids)
    adb_devices = parse_adb_devices(StringIO.StringIO(subprocess.check_output([adb_path, 'devices'])))
    return find_missing(resolved, adb_devices[:])

class MyHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_HEAD(s):
        s.send_response(200)
        s.send_header("Content-type", "application/json")
        s.end_headers()
    def do_GET(s):
        """Respond to a GET request."""
        s.send_response(200)
        s.send_header("Content-type", "application/json")
        s.end_headers()
        s.wfile.write(json.dumps(do_check()))



parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('--listen', dest='port', action='store', help='listen on the port',
metavar='int', type=int, choices=xrange(65536))
parser.add_argument('--adb', dest='adb_path', action='store', help='path to adb')

args = parser.parse_args()

if args.adb_path:
    adb_path = args.adb_path

else:
    if not 'ANDROID_HOME' in os.environ:
        print >> sys.stderr, "ANDROID_HOME must be set in the environment"
        exit(2)

    adb_path = os.path.join(os.environ['ANDROID_HOME'], 'platform-tools', 'adb')

if not os.path.exists(adb_path):
    print >> sys.stderr, "Could not find adb at %s" % adb_path
    exit(2)

if args.port:
    server_class = BaseHTTPServer.HTTPServer
    httpd = server_class(('', args.port), MyHandler)
    print time.asctime(), "Server Starts - %s:%s" % ('', args.port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    
else:
    missing = do_check()
    if len(missing) > 0:
        print >> sys.stderr, missing
        sys.exit(1)
