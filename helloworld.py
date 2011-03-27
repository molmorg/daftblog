import os

from google.appengine.ext.webapp import template
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

class Post(db.Model):
    legacy_post_id = db.StringProperty(required=False)
    title = db.StringProperty(required=True)
    link_title = db.StringProperty(required=True)
    body = db.StringProperty(required=True, multiline=True)
    posted_date = db.DateTimeProperty(required=True, auto_now_add=True)
    is_published = db.BooleanProperty(required=True, default=True)
    publish_date = db.DateTimeProperty(required=True, auto_now_add=True)
    user = db.UserProperty(required=True)
    
class Comment(db.Model):
    post = db.ReferenceProperty(required=True)
    name = db.StringProperty(required=True)
    comment = db.StringProperty(required=True, multiline=True)
    ip_address = db.StringProperty(required=True)
    posted_date = db.DateTimeProperty(required=True, auto_now_add=True)
    
class BlogUser(db.Model):
    user = db.UserProperty(required=True)
    display_name = db.StringProperty(required=True)

class Home(webapp.RequestHandler):
        
    def get(self):
        q = Post.all()
        q.order('-posted_date')
        posts = q.fetch(top_post_count)
        viewmodel = { 'posts' : posts }
        self.response.write(render_template('home.html'), viewmodel)
        
class New(webapp.RequestHandler):
    def get(self):
        self.response.write(render_template('new.html'), None)

application = webapp.WSGIApplication([('/', Home),
                                      ('/New', New)],
                                      debug=True)

def render_template(path, model):
    template.render(map_path(path), )

def map_path(path):
    return os.path.join(os.path.dirname(__file__), path)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

top_post_count = 20