# GTN/Gallantries Slack Bot

This bot will support Smörgåsbord style events where students run through tutorials in an asynchronous manner. This bot will be present in all training channels and participants will be able to use an action like

```
/completed <history>
```

And it will register that they've completed a tutorial/material associated with that channel (based on the mapping available from the Video Library).

When they've completed however much of the course they'd like to, they can run

```
/requestCertificate
```

and instructors will receive a message with which tutorials they're requesting + which histories. They can approve or deny any subset of those tutorials, and it will be sent back to the bot which will generate the PDF certificate for the participant and send it to them in Slack.
