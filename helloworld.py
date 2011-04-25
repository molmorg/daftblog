from google.appengine.dist import use_library
use_library('django', '1.2')
from google.appengine.ext.webapp import template
template.register_template_library('customtags.custom_tags')

import os
import cgi
import logging
import datetime
import urllib

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.api import urlfetch
from google.appengine.api import mail
from google.appengine.api import xmpp
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

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
    tags = db.StringListProperty(required=True)
    
class Tag(db.Model):
    name = db.StringProperty(required=True)
    
class Comment(db.Model):
    post = db.ReferenceProperty(required=True)
    name = db.StringProperty(required=True)
    email = db.EmailProperty(required=False)
    url = db.URLProperty(required=False)
    body = db.StringProperty(required=True, multiline=True)
    ip_address = db.StringProperty(required=True)
    posted_date = db.DateTimeProperty(required=True, auto_now_add=True)
    moderated = db.BooleanProperty(required=True, default=False)
    validated = db.BooleanProperty(required=True, default=False)
    
class BlogUser(db.Model):
    user = db.UserProperty(required=True)
    short_name = db.StringProperty(required=True)
    long_name = db.StringProperty(required=True)
    twitter_handle = db.StringProperty()
    bio_url = db.StringProperty()
    image_url = db.StringProperty()
    
def get_current_blog_user():
    current_user = users.get_current_user()
    blog_users = BlogUser.all().filter("user =", current_user).fetch(1, 0)
    if (len(blog_users) >= 1):
        return blog_users[0]
    else:
        if (users.is_current_user_admin() == False):
            return None
        else:
            new = BlogUser(
                           user = current_user,
                           long_name = current_user.user_id(),
                           short_name = current_user.nickname(),
                           )
            new.put()
            return new   
    
def reject_no_login(target):
    def wrapper(*kwargs):
        if (get_current_blog_user() == None):
            login_url = users.create_login_url(self.request.uri)
            self.response.set_status(401)
            self.response.out.write('You must be <a href="' + login_url + '">logged in</a> as admin')
            return
        else:
            target(*kwargs)
    return wrapper  

class Home(webapp.RequestHandler):
    def get(self):
        posts = get_top_posts()
        viewmodel = { 'posts' : posts, 'blog_model' : get_blog_model(self) }
        self.response.out.write(render_template('home.html', viewmodel))
        
class New(webapp.RequestHandler):
    @reject_no_login
    def get(self):
        tags = Tag.all()
        self.response.out.write(render_template('new.html', { 'post': None, 'blog_model' : get_blog_model(self), 'tags':tags} ))
    
    @reject_no_login
    def post(self):
        post = Post(
                    title = self.request.get('title'),
                    link_title = self.request.get('link_title'),
                    body = self.request.get('body'),
                    user = users.get_current_user(),
                    tags = self.request.get('hidden_tags').rsplit(';'))
        post.put()
        self.redirect('/')
        
class Edit(webapp.RequestHandler):
    @reject_no_login
    def get(self, link_title):
        post = get_post_by_link_title(link_title)
        if post == None:
            self.redirect('/' + link_title);
            return
        tags = Tag.all()
        self.response.out.write(render_template('new.html', { 'post': post, 'blog_model': get_blog_model(self), 'tags':tags }))
#TODO - implement POST
        
class View(webapp.RequestHandler):
    def get (self, link_title):
        post = get_post_by_link_title(link_title)
        if post == None:
            self.response.set_status(404)
            self.response.out.write('No post with title ' + link_title)
            return
        
        comments = Comment.all()
        comments.filter('post =', post)
        comments.order('-posted_date')
        
        viewmodel = {'post':post, 'comments':comments, 'blog_model' : get_blog_model(self) }    
        
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
        
        if (result.content[0:4] != 'true'):
            self.response.set_status(400)
            self.response.out.write('Invalid captcha, go back - please try again.')
            return
        
        post = get_post_by_link_title(link_title)
        
        comment = Comment(
                          post = post,
                          name = self.request.get('name'),
                          url = self.request.get('url'),
                          email = self.request.get('email'),
                          body = self.request.get('body'),
                          ip_address = self.request.remote_addr)
        comment.put()
        
        mail_view_model = {
                           'post' : post,
                           'comment' : comment,
                           'post_url' : self.request.url,
                           'host_url' : self.request.host_url,
                           }
        
        mail_body = render_template('commentMail.html', mail_view_model)
        
        logging.info(mail_body)
        
        mail.send_mail(sender="daftblob.com <admin@daftblog.com>",
                       to="admin@nowhere.com",
                       subject="New Comment on %s" %post.title,
                       body= mail_body)
        
        #TODO - provide a notification to the poster that his comment has been received
        #and should appear soon. Hide the comment form too. Consider using AJAX for this.
        self.redirect('{0}#{1}'.format(self.request.url, comment.key()))
        
class ModerateComment(webapp.RequestHandler):
    @reject_no_login
    def get(self, commentKey, validate):
        
        comment = db.get(commentKey)
        comment.moderated = True
        comment.validated = validate[0:4] == 'true'
        comment.put()
        
        post = comment.post
        #TODO - make the comment reveal!
        self.redirect('/{0}?revealComment={1}'.format(post.link_title, comment.key()), False)
        
class UploadFile(webapp.RequestHandler):
    @reject_no_login
    def get(self):
        upload_url = blobstore.create_upload_url('/upload')
        self.response.out.write(render_template('upload.html', {'upload_url' : upload_url}))
        
class UploadBlob(blobstore_handlers.BlobstoreUploadHandler):
    @reject_no_login
    def post(self):
        upload_files = self.get_uploads('file')  # 'file' is file upload field in the form
        blob_info = upload_files[0]
        self.redirect('/uploads/%s' % blob_info.filename)

class ServeBlob(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, resource):
        query = "WHERE filename='%s'" % resource
        blob_infos = blobstore.BlobInfo.gql(query).fetch(1,0)
        if (len(blob_infos) == 0):
            self.response.set_status(404)
            self.response.out.write('No such resource found: %s' % resource)
            return
        
        self.send_blob(blob_infos[0])
        
class DeleteComment(webapp.RequestHandler):
    @reject_no_login
    def get(self, link_title, comment_key):
        db.delete(comment_key)
        self.redirect('/%s' %link_title)
   
class RedirectToView(webapp.RequestHandler):
    def get(self, link_title):
        self.redirect("/" + link_title, True)

class PostFeed(webapp.RequestHandler):
    def get(self):
        posts = get_top_posts()
        self.response.out.write(render_template('feed.html', { 'posts' : posts, 'base_url' : '%s/' %  self.request.host_url  }))
    
class CommentFeed(webapp.RequestHandler):
    def get(self, link_title):
        post = get_post_by_link_title(link_title)
        comments = Comment.all().filter("post =", post)
        self.response.out.write(render_template('commentFeed.html', { 'post' : post, 'comments': comments, 'base_url' : '%s/' %  self.request.host_url  }))
    

application = webapp.WSGIApplication([('/', Home),
                                      ('/new', New),
                                      ('/uploadFile', UploadFile),
                                      ('/upload', UploadBlob),
                                      ('/([^/]+)/Comments/([^/]+)/delete', DeleteComment),
                                      ('/moderateComment/([^/]+)/(.*)', ModerateComment),
                                      ('/uploads/(.*)', ServeBlob),
                                      ('/Feed/([^/]+)/Comments', CommentFeed),
                                      ('/Feed', PostFeed),
                                      ('/Edit/([^/]+)', Edit),
                                      ('/([^/]+).aspx', RedirectToView),
                                      ('/([^/]+)', View)],
                                      debug=True)

top_post_count = 20

def get_top_posts():
# TODO - remove no cahce
    posts = None
    if (posts is None):
        q = Post.all()
        q.filter('publish_date <=', datetime.datetime.now())
        q.filter('is_published =', True)
        q.order('-publish_date')
        posts = q.fetch(top_post_count)
    return posts

def get_current_blog_user():
    current_user = users.get_current_user()
    blog_users = BlogUser.all().filter("user =", current_user).fetch(1, 0)
    if (len(blog_users) >= 1):
        return blog_users[0]
    else:
        if (users.is_current_user_admin() == False):
            return None
        else:
            new = BlogUser(
                           user = current_user,
                           long_name = current_user.user_id(),
                           short_name = current_user.nickname(),
                           )
            new.put()
            return new   
    
def reject_no_login(target):
    def wrapper(*kwargs):
        if (get_current_blog_user() == None):
            login_url = users.create_login_url(self.request.uri)
            self.response.set_status(401)
            self.response.out.write('You must be <a href="' + login_url + '">logged in</a> as admin')
            return
        else:
            target(*kwargs)
            

def get_blog_model(self):
# TODO - need to cache some of these pieces.
    return {
            'login_url': users.create_login_url(self.request.uri),
            'logout_url': users.create_logout_url(self.request.uri),
            'current_blog_user' : get_current_blog_user(),
            'is_admin': users.is_current_user_admin(),
            'role' : 'TBC'
            }

def get_post_by_link_title(link_title):
    q = Post.all()
    q.filter('link_title =', link_title)
    posts = q.fetch(1)
    return posts[0]

def render_template(path, model):
    return template.render(map_path(path), model)

def map_path(path):
    mapped = os.path.join(os.path.dirname(__file__), path)
    return mapped

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

