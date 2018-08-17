import getopt, shlex, pycurl
import time, json, io
import threading, queue
import logging
from urllib.parse import urlencode
from .userblr import Userblr
from .chatblr import Chatblr
from .msgblr import Msgblr, TextMsg, ImageMsg


logger = logging.getLogger(__package__)


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
		if others:
			others = {
				'notifications': True,	# reblog, like, etc notfications
				'unread': True,	# news feed unread
				'inbox': True}	# asks (and submissions, maybe)
			return self._counts(others=others)
		else:
			return self._counts()['unread_messages']


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


	def poll(self, chat_id, queue, sleep_time=1, sleep_threshold=600):
		"""
		Poll for new messages (incoming and outgoing) in `chat_id` and enqueue to `queue`.
		New messages that are available before polling starts are discarded.
		`queue` is a `queue` object (only `put_nowait` method is used.)
		`sleep_time` is either a tuple of two: sleep time in normal phase,
		and sleep time in sleep phase; or a number that will be used in both.
		`sleep_threshold` is the number of seconds after the last msg after which
		`poll` will enter sleep phase. In sleep phase, we don't query messages
		from Tumblr until we know of the existence of new ones via `self.get_counts`.
		"""

		if not hasattr(sleep_time, '__getitem__'):
			sleep_time = (sleep_time,)*2

		last_ts = time.time()

		def sleep_phase(v=None):
			if v == None:
				return sleep_phase.on
			elif v == True and sleep_phase.on == False:
				sleep_phase.on = True
				logger.debug(f'Sleep phase activated. Interval: {sleep_time[1]}')
			elif v == False and sleep_phase.on == True:
				sleep_phase.on = False
				logger.debug(f'Sleep phase deactivated. Normal Interval: {sleep_time[0]}')
		sleep_phase.on = False

		def check_for_new(chat_id):
			if sleep_phase() and not self.get_counts().get(chat_id):
				return []

			messages = self.get_messages(chat_id)

			# getting old last_ts and saving the new one
			# If we delay this operation until filtering old msgs, we'd
			# risk `messages` being empty which will raise an exception.
			# So we do it here. But we still need the old value, so we
			# make a copy of it. Good?
			nonlocal last_ts
			last_ts_copy = last_ts
			last_ts = messages[-1].date

			# eliminate messages already gotten
			while messages and messages[0].date <= last_ts_copy:
				messages.pop(0)

			# We can work here on the case of msgs that are not al-
			# ready gotten but were not included with the new msgs
			# received. However I think it is very  unlikely for
			# this to happen if you don't send more than 10 msgs
			# in a period of 1s for example :new_moon_with_face:

			return messages
			# all of what I said before is crap and
			# and is not the perfect way to do shit
			# I wrote and two times just to respect
			# the line width because it looks good.

		def enqueue_new(new_msgs):
			if new_msgs:
				logger.debug(f'Got {len(new_msgs)} new messages. Enqueuing them.')
			for msg in new_msgs:
				queue.put_nowait(msg)

		def sleep_handler(last_ts):
			tdelta = time.time() - last_ts
			if tdelta <= sleep_threshold:
				sleep_phase(False)
				time.sleep(sleep_time[0])
			else:
				sleep_phase(True)
				time.sleep(sleep_time[1])


		logger.debug(f'Entering poll loop for chat{chat_id}')
		while True:
			new_msgs = check_for_new(chat_id)

			enqueue_new(new_msgs)

			sleep_handler(last_ts)


	def _counts(self, **kwargs):
		"""
		`additional_opts` list of (pycurl.OPT, val) for pycurl object
		`others` dict of query parametres
		"""
		key = self._key
		query_opts = {'method': methods.GET}
		query_opts['endpoint'] = 'https://www.tumblr.com/svc/user/counts'
		query_opts['params'] = {
			'mention_keys': key,	# eliminate other blogs counts
			'unread_messages': True,	# This is what we care for
			}

		if 'others' in kwargs:
			others = kwargs['others']
			query_opts['params'].update(others)

		if 'additional_opts' in kwargs:
			additional_opts = kwargs['additional_opts']
			query_opts['additional_opts'] = additional_opts

		result = self._query(**query_opts)

		# if status is 'ok', result do not have 'meta'
		# if there IS a 'meta', we could do a check (although not necessary)
		if 'meta' in result:
			_is_meta_ok(result)

		if key in result['unread_messages']:
			result['unread_messages'] = result['unread_messages'][key]

		if 'next_from' in result:
			del result['next_from']

		return result


	def _query(self, method, endpoint, params, additional_opts=[]):
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

		# merging option from additional_opts
		for item in additional_opts:
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


