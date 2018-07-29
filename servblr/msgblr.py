

def _short_user_id(user_id):
	return user_id.split('.')[0]

def _ts_float(ts):
	if type(ts) is float:
		return ts
	else:
		ts = str(ts)
		return float(ts[:10]+'.'+ts[-3:])


class Msgblr(object):
	@staticmethod
	def de_json(json, chat=None):
		"""returns Msgblr instances from a JSON.
		A JSON message object does not have the 
		`chat` field so it must be provided as
		argument. Set to `None` if not."""

		if json['type'] == 'TEXT':
			return TextMsg( text = json['message'],
				chat = chat,
				author = _short_user_id(json['participant']),
				date = _ts_float(json['ts']))

		elif json['type'] == 'IMAGE':
			return ImageMsg(image_url = json['images'][0]['original_size']['url'],
			chat = chat,
			author = _short_user_id(json['participant']),
			date = _ts_float(json['ts']))

		elif json['type'] == 'POSTREF':
			return PostMsg(
				post= json['post'],
				chat = chat,
				author = _short_user_id(json['participant']),
				date = _ts_float(json['ts']))

		else:
			raise TypeError


class TextMsg(Msgblr):
	def __init__(self, text, chat, author, date):
		self.text = text
		self.chat = chat
		self.author = author
		self.date = date


class ImageMsg(Msgblr):
	def __init__(self, image_url, chat, author, date):
		self.image_url = image_url
		self.chat = chat
		self.author = author
		self.date = date


class PostMsg(Msgblr):
	def __init__(self, post, chat, author, date):
		self.post = post
		self.chat = chat
		self.author = author
		self.date = date

