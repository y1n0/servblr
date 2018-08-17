 - **get_messages limit:**
Tumblr server only returns a maximum of 20 messages, but the `get_messages`
method should be able to return whatever number specified. The current 
behavior is that it passes `limit` it is called with to Tumblr and returns
what it receives from the server as it is.

 - **poll queue outgoing messages ASAP:**
 The current behavior is that it does not retrieve messages until there an
unread indicator. That indicator only indicates that are new incoming messages.
So there might be 

- Msgblr should have a kinda of next prev method to get older newer msgs

- Enforce attribute types. e.g, `Chatbrl.chat_id`, is it `str` or `int`?
