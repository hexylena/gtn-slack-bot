from slack_bolt import App

import os
if 'SLACK_BOT_TOKEN' not in os.environ:
    class AppMock:
        def event(self, *a, **kw):
            return self.event

        def command(self, *a, **kw):
            return self.event

        def listener_runner(self, *a, **kw):
            o = object()
            setattr(o, 'logger', lambda *a, **kw: print(a, kw))
            return o

    app = AppMock()
else:
    app = App(
        token=os.environ.get("SLACK_BOT_TOKEN", ""),
        signing_secret=os.environ.get("SLACK_SIGNING_SECRET", ""),
        # disable eagerly verifying the given SLACK_BOT_TOKEN value
        token_verification_enabled=True,
    )
