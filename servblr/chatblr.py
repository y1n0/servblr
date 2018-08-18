from .userblr import Userblr

class Chatblr(object):
	def __init__(self, chat_id, servblr=None, **kwargs):
		self.chat_id = chat_id
		self.last_read = kwargs.get('last_read')
		self.last_modified = kwargs.get('last_modified')
		self.unread = kwargs.get('unread')
		self.participant = kwargs.get('participant')

		if servblr:
			self.servblr = servblr


	def participant_id(self):
		"""shortcut for Chatbr.participant.user_id"""
		return self.participant.user_id


	def get_count(self):
		"""return the number of new unread messages in the chat"""
		counts = self.servblr.get_counts()
		n = counts.get(str(self.chat_id), 0)
		self.unread = n
		return n


	def get_messages(self, **kwargs):
		"""shortcut for `Servblr.get_messages(Chatbr.chat_id, **kwargs)`"""
		if not hasattr(self, 'servblr'):
			raise Exception('this chat does not have a servblr')

		return self.servblr.get_messages(self.chat_id, **kwargs)


	def send_text(self, text, **kwargs):
		"""shortcut for `Servblr.send_text(Chatbr.chat_id, text)`"""
		if not hasattr(self, 'servblr'):
			raise Exception('this chat does not have a servblr')

		return self.servblr.send_text(self.chat_id, text, **kwargs)


	def send_image(self, image, **kwargs):
		"""shortcut for `Servblr.send_image(Chatbr.chat_id, image)`"""
		if not hasattr(self, 'servblr'):
			raise Exception('this chat does not have a servblr')

		return self.servblr.send_image(self.chat_id, image, **kwargs)


	def send_post(self, post, post_blog=None, **kwargs):
		"""shortcut for `Servblr.send_post(Chatbr.chat_id, **kwargs)`"""
		if not hasattr(self, 'servblr'):
			raise Exception('this chat does not have a servblr')

		return self.servblr.send_post(self.chat_id, post, post_blog, **kwargs)


	def poll(self, queue, **kwargs):
		"""shortcut for `Servblr.poll(Chatbr.chat, queue, **kwargs)`"""
		if not hasattr(self, 'servblr'):
			raise Exception('this chat does not have a servblr')

		return self.servblr.poll(self.chat_id, queue, **kwargs)


	@classmethod
	def de_json(cls, json):
		chat_id = json['id']
		last_read = json['last_read_ts']
		last_modified = json['last_modified_ts']
		unread_count = json['unread_messages_count']
		c = cls(chat_id,
				unread=unread_count,
				last_read=last_read,
				last_modified=last_modified )

		p = json['participants'][0]
		if p.get('admin'):
			p = json['participants'][1]

		c.participant = Userblr.de_json(p)
		return c
