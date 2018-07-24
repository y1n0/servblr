

class Userblr(object):
	def __init__(self, user_id, **kwargs):
		self.user_id = user_id
		self.last_active = kwargs.get('last_active')
		self.url = kwargs.get('url')

	@classmethod
	def de_json(cls, json):
		name = json['name']
		updated = json['updated']
		url = json['url']
		return cls(name, last_active=updated, url=url)

