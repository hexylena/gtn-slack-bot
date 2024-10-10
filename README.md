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

## Open Questions

- Register for events? How do we know which certificates are for which events? (Last N weeks?)
	- If they're running /completed and haven't registered, we could ask which event this is part of and give some 'select' boxes which are created from the video library events data?
- Multilingual for Spanscriptomics
- Changing the output of a certificate when we don't think they've achieved all of the tutorials?
- Need to ensure there's no conflicts between multiple tutorials pointing at a single channel (or that we're ok with it.)

## Why

- We get even better data of who actually did which tutorials
- We can automatically congratulate them in the channel and prompt them to make suggestions there or tell us what they thought about it, or one thing they wished it answered. This is a much more direct CTA than currently.
- Instructors get a very very good view of which tutorials are being completed when.
- The bot can control that a history is public and datasets shared properly and offer advice when it isn't, how to make their history public, instructions for sharing, etc.

