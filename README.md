# slack-channel-archiver

My previous work on processing slack messages (![slack-export-tools](https://github.com/hollyroberts/slack-export-tools)) was designed for archives. This takes the back end from that and instead uses the Slack Web API. Initially this could only be used for DMs, but when the conversations API got released I updated this to support all channel types.  

Because of the overlap between projects and bad architecture of both I'm trying to unify these various projects under ![slack-tools](https://github.com/hollyroberts/slack-tools)