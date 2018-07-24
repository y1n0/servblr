# servblr
A Tumblr instant messages wrapper in Python

# Quickstart

```python
import servblr

# Authorization is done via cookies (Do not talk to me about it.)
# Copy a request made to tumblr in cUrl format and use it to initialize
# the 'servblr'.
curl_cmd = ''
s = servblr.Servblr(curl_cmd)

# Now you can get the list of your conversations:
chats = s.get_chats()

# Or send a message (for that we'll need a convo id):
chat_id = chats[0].chat_id
s.send_message(chat_id, 'a msg')
```
