#!/usr/bin/python
import code
import getpass
import sys
import os
import logging

gdir = "/Applications/GoogleAppEngineLauncher.app/Contents/Resources/GoogleAppEngine-default.bundle/Contents/Resources/google_appengine"
ydir = os.path.join(gdir, "lib","yaml","lib")
fdir = os.path.join(gdir, "lib", "fancy_urllib")

logging.info(ydir)
sys.path.append(gdir)
sys.path.append(ydir)
sys.path.append(fdir)

from google.appengine.ext.remote_api import remote_api_stub
from google.appengine.ext import db

def auth_func():
    return raw_input('Username:'), getpass.getpass('Password:')

if len(sys.argv) < 2:
    print "Usage: %s app_id [host]" % (sys.argv[0],)
app_id = sys.argv[1]
if len(sys.argv) > 2:
    host = sys.argv[2]
else:
    host = '%s.appspot.com' % app_id

remote_api_stub.ConfigureRemoteDatastore(app_id, '/remote_api', auth_func, host)

code.interact('App Engine interactive console for %s' % (app_id,), None, locals())
  