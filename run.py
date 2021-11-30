from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import time
import os
import sqlite3

con = sqlite3.connect('transcript.sqlite3', check_same_thread=False)
cur = con.cursor()

SLACK_BOT_TOKEN = os.environ['SLACK_BOT_TOKEN']
SLACK_APP_TOKEN = os.environ['SLACK_APP_TOKEN']

app = App(token=SLACK_BOT_TOKEN)


def updateTranscript(user_id, channel, proof):
    cur.execute("insert into transcript values (?, ?, ?)", (user_id, channel, proof))
    con.commit()

def registerCertificateRequest(user_id, course):
    cur.execute("INSERT INTO certificate_request(user_id, course, time, approved) VALUES(?, ?, ?, 0)", (user_id, course, time.time()))
    con.commit()

def listPendingCertificateRequests(course):
    results = []
    for row in cur.execute('SELECT user_id, course, time from certificate_request where approved = 0 and id in (select max(id) from certificate_request group by user_id, course)'):
        results.append(row)

    msg = f"There are {len(results)} pending certificate requests:\n"
    for row in results:
        msg += f"<@{row[0]}> for {row[1]} at {row[2]} \n"
    return msg


# @app.event("app_mention")
# def mention_handler(body, say):
    # __import__('pprint').pprint(body)
    # say(f'Hello ')


def processCompleted(user_id, channel_name, text):
    if text.strip().lower().startswith('help'):
        return 'This command lets you register that you have completed a tutorial. Please run this command in the appropriate channel for that tutorial like so: `/completed <url to your shared galaxy history>`'

    if len(text.strip()) == 0:
        return f":warning: Hey <@{user_id}>, in order to use this command you need to provide some proof you completed this history. You can do that by making your history public and sharing a link to your history with us. Just re-run this command with `/completed <url to your shared galaxy history>`"

    updateTranscript(user_id, channel_name, text)
    return "Received! We've added this to your transcript. If you want to add more histories, please run this command again with any other 'proof' of completing the tutorial."


@app.command("/completed")
def handle_completed(ack, body, logger):
    try:
        msg = processCompleted(body['user_id'], body['channel_name'], body['text'])
        ack(msg)
    except Exception as e:
        logger(e)
        ack("Something went wrong! We could not record your completion. Please contact <@U01F7TAQXNG>")


def processCertifyRequest(user_id, text):
    if text.strip().lower().startswith('help'):
        return 'This command lets you request your certificate, a human will review the request before approving it. Please supply the event name for which you are requesting your certificate. Your options are: gcc2021, ...'

    if text != 'gcc2021':
        return 'This command lets you request your certificate, a human will review the request before approving it. Please supply the event name for which you are requesting your certificate. Your options are: gcc2021, ...'

    registerCertificateRequest(user_id, text)
    return 'We have successfully recorded your request! A human will review it and will respond to you within two weeks with your certificate'


@app.command("/certify")
def handle_certify(ack, body, logger):
    try:
        msg = processCertifyRequest(body['user_id'], body['text'])
        ack(msg)
    except Exception as e:
        print(e)
        ack("Something went wrong! We could not record your request. Please contact <@U01F7TAQXNG>")

@app.command("/listpendingcertificaterequests")
def handle_pendingRequests(ack, body, logger, say):
    if body['user_id'] != 'U01F7TAQXNG':
        ack("You are not allowed to run this command")
        return
    ack()

    try:
        msg = listPendingCertificateRequests(body['text'].split(' ')[0].lower())
        say(msg)
    except Exception as e:
        print(e)
        say("Something went wrong! We could not record your request. Please contact <@U01F7TAQXNG>")


# @app.message(":wave:")
# def say_hello(message, say):
    # user = message['user']
    # say(f"Hi there, <@{user}>!")

if __name__ == "__main__":
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
