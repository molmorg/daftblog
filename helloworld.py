from google.appengine.dist import use_library
use_library('django', '1.2')

import os
import cgi
import logging
import datetime
import urllib

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.api import urlfetch
from google.appengine.ext.webapp import template
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
    enable_comments = db.BooleanProperty(required=True, default=True)
    
class Comment(db.Model):
    post = db.ReferenceProperty(required=True)
    name = db.StringProperty(required=True)
    email = db.EmailProperty(required=False)
    url = db.URLProperty(required=False)
    body = db.StringProperty(required=True, multiline=True)
    ip_address = db.StringProperty(required=True)
    posted_date = db.DateTimeProperty(required=True, auto_now_add=True)
    moderated = db.BooleanProperty(required=True, default=False)
    validated = db.BooleanProperty(required=True, default=True)
    
class BlogUser(db.Model):
    user = db.UserProperty(required=True)
    display_name = db.StringProperty(required=True)
    role = db.StringProperty(required=True)

class Home(webapp.RequestHandler):
        
    def get(self):
        q = top_posts_query()
        posts = q.fetch(top_post_count)
        viewmodel = { 'posts' : posts }
        self.response.out.write(render_template('home.html', viewmodel))
        
class New(webapp.RequestHandler):
    def get(self):
        if check_login(self) == False:
            return
        self.response.out.write(render_template('new.html', None))
        
    def post(self):
        if check_login(self) == False:
            return
        post = Post(
                    title = self.request.get('title'),
                    link_title = self.request.get('link_title'),
                    body = self.request.get('body'),
                    user = users.get_current_user())
        post.put()
        self.redirect('/')
        
class View(webapp.RequestHandler):
    def get (self, link_title):
        
        post = get_post_by_link_title(link_title)
        
        if post == None:
            self.response.set_status(404)
            self.response.out.write('No post with title ' + link_title)
            return
        
        comments = Comment.all()
        comments.filter('validated =', True)
        comments.filter('post =', post)
        comments.order('-posted_date')
        
        viewmodel = {'post':post, 'comments':comments}    
        
        self.response.out.write(render_template('view.html', viewmodel ))

    def post (self, link_title):
        url = 'http://www.google.com/recaptcha/api/verify'
        form_data = urllib.urlencode(
             {
                'privatekey' : '6LdwKcMSAAAAAH59DAAGottMXK7ih7w5rX3e-QAP',
                'remoteip' : self.request.remote_addr,
                'challenge' : self.request.get('recaptcha_challenge_field'),
                'response' : self.request.get('recaptcha_response_field')
              })
        
        result = urlfetch.fetch(url=url,
                          payload=form_data,
                          method = urlfetch.POST)
        
        logging.info(result.content)
        if (result.content[0:4] != 'true'):
            self.response.set_status(400)
            self.response.out.write('Invalid captcha, go back - please try again.')
            return
        
        comment = Comment(
                          post = get_post_by_link_title(link_title),
                          name = self.request.get('name'),
                          url = self.request.get('url'),
                          email = self.request.get('email'),
                          body = self.request.get('body'),
                          ip_address = self.request.remote_addr)
        comment.put()
        
        self.redirect(self.request.uri)
        
class RedirectToView(webapp.RequestHandler):
    def get(self, link_title):
        self.redirect("/" + link_title, True)

application = webapp.WSGIApplication([('/', Home),
                                      ('/New', New),
                                      ('/(.*).aspx', RedirectToView),
                                      ('/(.*)', View)],
                                      debug=True)

top_post_count = 20

def top_posts_query():
        q = Post.all()
        q.filter('publish_date <=', datetime.datetime.now())
        q.filter('is_published =', True)
        q.order('-publish_date')
        return q
        

def check_login(self):
    if (users.is_current_user_admin() == False):
        login_url = users.create_login_url(self.request.uri)
        self.response.set_status(401)
        self.response.out.write('You must be <a href="' + login_url + '">logged in</a> as admin')
        return False
    else:
        return True

def std_model(self):
# TODO - need to cache some of these pieces.
    return {
            'login_url': users.create_login_url(self.request.uri),
            'logout_url': users.create_logout_url(self.request.uri),
            'user' : users.get_current_user(),
            'role' : 'TBC'
            }
    
    
def get_post_by_link_title(link_title):
    q = Post.all()
    q.filter('link_title =', link_title)
    posts = q.fetch(1)
    if (len(posts) < 1):
        return None
    
    return posts[0]

def render_template(path, model):
    return template.render(map_path(path), model)

def map_path(path):
    mapped = os.path.join(os.path.dirname(__file__), path)
    logging.info(mapped)
    return mapped

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

