import os
from google.appengine.ext.webapp import template 

def render_post(post):
    return { 'post': post }

def map_path(path):
    return os.path.join(os.path.dirname(__file__), path)

register = template.create_template_register()
register.inclusion_tag(map_path('post.html'))(render_post)
    