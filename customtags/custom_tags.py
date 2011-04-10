import os
from google.appengine.ext.webapp import template 

def render_post(post):
    return { 'post': post }

def render_comment(comment, post, blog_model):
    return {'comment': comment, 'post': post, 'blog_model': blog_model}

def map_path(path):
    return os.path.join(os.path.dirname(__file__), path)

register = template.create_template_register()
register.inclusion_tag(map_path('post.html'))(render_post)
register.inclusion_tag(map_path('comment.html'))(render_comment)
    