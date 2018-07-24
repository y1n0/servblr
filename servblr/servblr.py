import getopt, shlex, pycurl
import time, json, io
from urllib.parse import urlencode
from .userblr import Userblr
from .chatblr import Chatblr
from .msgblr import Msgblr, TextMsg, ImageMsg



def _long_user_id(user_id):
	return user_id+'.tumblr.com'


def _ts_format(ts):
	return str(ts).replace('.', '')[:13].ljust(13, '0')


def _is_meta_ok(result):
	"""used to check if results are valid, i.e. code is 200.
	Otherwise it raises an exception with the error msg.
	"""
	if result['meta']['status'] != 200:
		status = result['meta']['msg']
		raise Exception(status)


class methods:
	GET = 42
	POST = 53
	POST_MULTI = 23


class Servblr:
	def __init__(self, curl_cmd):

		def get_servblr_info():
			result = self._query(
				methods.GET,
				'https://www.tumblr.com/svc/conversations',
				{})

			_is_meta_ok(result)

			p = result['response']['conversations'][0]['participants'][0]
			if not ( p.get('admin') and p.get('primary') ):
				p = result['response']['conversations'][0]['participants'][1]

			d = {'whoami': p['name'],
				'_key': p['mention_key']}

			return d

		recognized_opts = ['compressed', 'data']
		# we should act on this self._query (use self._curl_opts)

		cmd_args = shlex.split(curl_cmd)[1:]
		options, arguments = getopt.gnu_getopt(cmd_args, 'H:', recognized_opts)

		self.headers = [ val for opt, val in options if opt == '-H' ]
		self._curl_opts = set() # items should be `tuple(pycurl.OPT, VAL)`
		info = get_servblr_info()
		for k, v in info.items():
			setattr(self, k, v)


	def get_counts(self, others=False):
		key = self._key
		endpoint = 'https://www.tumblr.com/svc/user/counts'
		params = {
			'mention_keys': key,	# eliminate other blogs counts
			'unread_messages': True,	# This is what we care for
			}

		if others:
			others = {
				'notifications': True,	# reblog, like, etc notfications
				'unread': True,	# news feed unread
				'inbox': True}	# asks (and submissions, maybe)
			params.update(others)

		result = self._query(methods.GET, endpoint, params)

		# if status is 'ok', result do not have 'meta'
		if 'meta' in result:
			_is_meta_ok(result)

		if key in result['unread_messages']:
			result['unread_messages'] = result['unread_messages'][key]

		return result


	def get_chats(self):
		endpoint = 'https://www.tumblr.com/svc/conversations'
		params = {'participant': _long_user_id(self.whoami)}
		result = self._query(methods.GET, endpoint, params)

		_is_meta_ok(result)

		chats = list()
		for c in result['response']['conversations']:
			_temp = Chatblr.de_json(c)
			_temp.servblr = self
			chats.append(_temp)

		return chats


	def get_messages(self, chat_id, before=0, after=0, limit=0, only_incoming=False):
		"""
		`before' takes a UNIX time in the form of `str', or `int'.
				Used to retrieve older msgs.
		`after' takes a value greater than the second element of
				the tuple `poll' returns.
				Used to reset unread counter
		The maximum `limit' the server returns is 20. But we can
		enforce whatever value we want internanlly (not implemented
		yet.) If used with `only_incoming=True`, the results
		returned may be less that `limit'.

		NOTE: older messages are first in the returned list.
		"""
		endpoint = 'https://www.tumblr.com/svc/conversations/messages'
		params = {
			'conversation_id': chat_id,
			'participant': _long_user_id(self.whoami)}

		if before:
			params['before'] = _ts_format(before)
		if limit:
			params['limit'] = limit
		if after:
			params['_'] = after

		result = self._query(methods.GET, endpoint, params)

		_is_meta_ok(result)

		payload = result['response']['messages']['data']
		messages = list()
		for msg in payload:
			if only_incoming and msg['participant'].startswith(self.whoami):
				continue
			_temp = Msgblr.de_json(msg, chat_id)
			messages.append(_temp)

		return messages


	def send_text(self, chat_id, text):
		endpoint = 'https://www.tumblr.com/svc/conversations/messages'
		params = {
			'conversation_id': chat_id,
			'message': text,
			'type': 'TEXT',
			'participant': _long_user_id(self.whoami),
			'participants': ''}

		result = self._query(methods.POST, endpoint, params)

		_is_meta_ok(result)

		msg = result['response']['messages']['data'][0]
		msg = Msgblr.de_json(msg, chat_id)

		return msg


	def send_image(self, chat_id, image):
		endpoint = 'https://www.tumblr.com/svc/conversations/messages'
		params = {
			'conversation_id': chat_id,
			'type': 'IMAGE',
			'participant': _long_user_id(self.whoami),
			'participants': '', 
			'context' : 'messaging-image-upload'}

		if type(image) == bytes:
			# random string for the filename would be better 
			params['data'] = (pycurl.FORM_BUFFER, 'image.jpg', pycurl.FORM_BUFFERPTR, image)
		elif type(image) == str:
			params['data'] = (pycurl.FORM_FILE, image)
		else:
			raise TypeError('exptected str for a path or bytes.')

		params = [ (k, v) for k, v in params.items() ]

		result = self._query(methods.POST_MULTI, endpoint, params)

		_is_meta_ok(result)

		msg = result['response']['messages']['data'][0]
		msg = Msgblr.de_json(msg, chat_id)

		return msg


	def _query(self, method, endpoint, params):
		res_buffer = io.BytesIO()
		c = pycurl.Curl()
		c.setopt(pycurl.VERBOSE, 0)
		c.setopt(pycurl.WRITEDATA, res_buffer)
		c.setopt(pycurl.HTTPHEADER, self.headers)
		c.setopt(pycurl.ACCEPT_ENCODING, 'deflate, gzip')
		# c.setopt(pycurl.DEBUGFUNCTION, lambda i,j:print(j))
		# Cookies are not getting modified with here-in requests
		# no need for cookie engine
		# c.setopt(pycurl.COOKIEFILE, self.cookies_path)
		# c.setopt(pycurl.COOKIEJAR, self.cookies_path)

		# merging option from self._curl_opts
		for item in self._curl_opts:
			c.setopt(*item)

		if method == methods.GET:
			url = endpoint + '?' + urlencode(params)
			c.setopt(pycurl.HTTPGET, 1)
		elif method == methods.POST:
			payload = urlencode(params)
			url = endpoint
			c.setopt(pycurl.POSTFIELDS, payload)
		elif method == methods.POST_MULTI:
			c.setopt(pycurl.HTTPPOST, params)
			url = endpoint

		c.setopt(pycurl.URL, url)
		c.perform()
		c.close()

		global _b	# for debugging
		_b = res_buffer

		res_buffer.seek(0)
		return json.load(res_buffer)

