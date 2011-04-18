import os
import urllib2
import MultipartPostHandler

from google.appengine.ext import blobstore

path = "/Users/josh/Downloads/wwwroot/Uploads"
opener = urllib2.build_opener(MultipartPostHandler.MultipartPostHandler)
files = os.listdir(path)

def start():
    for file in files:
        full_path = os.path.join(path, file)
        if (os.path.isfile(full_path)):
            print file
            url = blobstore.create_upload_url('/upload')
            print url
            params = { 'file' : open(full_path)}
            opener.open(url, params)
            