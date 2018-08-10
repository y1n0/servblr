 - **get_messages limit:**
Tumblr server only returns a maximum of 20 messages, but the `get_messages`
method should be able to return whatever number specified. The current 
behavior is that it passes `limit` it is called with to Tumblr and returns
what it receives from the server as it is.