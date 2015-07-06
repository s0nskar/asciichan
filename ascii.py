import os
import re
import sys
import urllib2
import json
from string import letters

import jinja2
import webapp2

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__),"templates")
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
								autoescape = True)


class Handler(webapp2.RequestHandler):
	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)

	def render_str(self, template, **params):
		t = jinja_env.get_template(template)
		return t.render(params)

	def render(self, template, **kw):
		self.write(self.render_str(template, **kw)) 

IP_URL = "http://ipinfo.io/%s/json"
def get_coord(ip):
	#ip = '4.2.2.2'
	url = IP_URL %ip
	content = None
	try:
		content = urllib2.urlopen(url).read()
	except urllib2.URLError:
		return None

	if content:
		json_o = json.loads(content)
		if not 'bogon' in json_o:
			lat,lon = json_o['loc'].split(',')
			return db.GeoPt(lat, lon)

GMAPS_URL = 'http://maps.googleapis.com/maps/api/staticmap?size=1200x350&sensor=false&'
def gmaps_img(points):
	markers = '&'.join('markers=%s,%s'%(p.lat,p.lon)
						for p in points)
	return GMAPS_URL + markers

class Art(db.Model):
	title = db.StringProperty(required = True)
	art = db.TextProperty(required = True)
	created = db.DateTimeProperty(auto_now_add = True)
	coords = db.GeoPtProperty()

class MainPage(Handler):
	def render_front(self,title="",art="",error=""):
		arts = db.GqlQuery("SELECT * FROM Art "
							"ORDER BY created DESC "
							"LIMIT 10")
		arts = list(arts)

		points = filter(None, (a.coords for a in arts))
		img_url = None

		if points:
			img_url = gmaps_img(points)
		self.render("ascii.html",title=title,art=art,error=error,arts = arts,img_url=img_url)

	def get(self):
		#self.write(repr(get_coord(self.request.remote_addr)))
		#self.write(self.request.remote_addr)
		self.render_front()

class NewPost(Handler):
	def get(self):
		self.render("new_art.html")

	def post(self):
		title = self.request.get("title")
		art = self.request.get("art")
		if title and art:
			a = Art(title = title,art=art)
			coords = get_coord(self.request.remote_addr)
			if coords:
				a.coords = coords
			a.put()
			self.redirect("/")
		else:
			error = "We need both a title and artwork!!"
			self.render("new_art.html",title=title,art=art,error=error)

app = webapp2.WSGIApplication([('/', MainPage),
								('/new',NewPost)],
								 debug=True)
