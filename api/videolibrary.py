import os
import isodate
from datetime import datetime, timedelta
import requests
import re
import json
from .models import Transcript, CertificateRequest


file_path = os.path.dirname(os.path.abspath(__file__))
videosjson = os.path.join(file_path, "videos.json")
with open(videosjson, "r") as handle:
    videos = json.load(handle)

sessionsjson = os.path.join(file_path, "sessions.json")
with open(sessionsjson, "r") as handle:
    sessions = json.load(handle)

gtnjson= os.path.join(file_path, "gtn.json")
with open(gtnjson, "r") as handle:
    gtndata = json.load(handle)

studyloadjson = os.path.join(file_path, "studyload.json")
with open(studyloadjson, "r") as handle:
    studyloaddata = json.load(handle)

def convert_name(path):
    path_parts = path.split("/")
    if path_parts[0] == "statistics":
        path_parts[0] = "machine_learning"
    if path_parts[0] == "sequence-analysis":
        path_parts[0] = "ngs"

    if "galaxy/intro" in path or path_parts[0] == "introduction":
        return "galaxy-intro"
    elif path_parts[0] in ("galaxy", "community", "webinar"):
        return "general"
    elif path_parts[0] == "course":
        # These are specific to their events
        return "-".join(["event", path_parts[1].replace("welcome-", "")])
    elif path_parts[0] == "contributing":
        return "gtn"
    elif "tool-generators" in path_parts[1]:
        return "dev-toolfactory"
    elif len(path_parts) > 2 and path_parts[2] in ("tutorial", "slides"):
        return "_".join(path_parts[0:2])
    elif len(path_parts) > 2:
        return "_".join(path_parts[0:2])
    elif len(path_parts) == 2:
        return "_".join(path_parts[0:2])
    return None


INVERTED_SESSIONS = {}
for k, v in sessions.items():
    for vid in v["videos"]:
        INVERTED_SESSIONS[vid] = k

CHANNEL_MAPPING = {}
for k, v in videos.items():
    if "support_channel" in v:
        c = v["support_channel"]
    else:
        c = convert_name(k)

    if c not in CHANNEL_MAPPING:
        CHANNEL_MAPPING[c] = []

    if k in INVERTED_SESSIONS:
        CHANNEL_MAPPING[c].append("session:" + INVERTED_SESSIONS[k])
    else:
        CHANNEL_MAPPING[c].append("video:" + k)

CHANNEL_MAPPING = {k: list(set(v)) for k, v in CHANNEL_MAPPING.items()}
for k, v in list(CHANNEL_MAPPING.items()):
    CHANNEL_MAPPING[k.lower()] = v

CHANNEL_GROUPS = list(set([
    x.split('_')[0] for x in
    CHANNEL_MAPPING.keys()
]))
CHANNEL_GROUPS = [
    x for x in CHANNEL_GROUPS
    if not x.startswith('event')
]


def channel2module(body):
    # Just a safe fail condition that doesn't disturb students
    if body["channel_name"] not in CHANNEL_MAPPING:
        return "channel:" + body["channel_name"]

    real_module = CHANNEL_MAPPING[body["channel_name"]]
    if len(real_module) == 1:
        module = real_module[0]
    else:
        module = "channel:" + body["channel_name"]
    return module


def validateGalaxyURLs(text):
    warnings = []
    fatal = []
    please = "Please submit the URL to your own Galaxy history for this tutorial."
    if "https://" not in text:
        fatal.append(":octagonal_sign: We could not find a url in your submission")
        return (warnings, fatal)

    if (
        "https://youtube.com" in text
        or "https://youtu.be" in text
        or "https://www.youtube.com" in text
    ):
        fatal.append(
            f":octagonal_sign: Please do not submit the YouTube urls, we do not need it. {please}"
        )

    if "https://gallantries.github.io" in text:
        fatal.append(
            f":octagonal_sign: Please do not submit the Schedule's URL, we do not need it. {please}"
        )

    if "interactivetoolentrypoint.interactivetool" in text:
        fatal.append(
            f":octagonal_sign: Please do not submit the URL to your interactive tools, we do not need to access them. Instead a history is better with any outputs from your interactive tool session (e.g. jupyter/rstudio) saved back to your history. {please}"
        )

    if "https://usegalaxy.xx/u/saskia/h/my-history-name" in text:
        fatal.append(f":octagonal_sign: This is the example URL. {please}")

    if "https://training.galaxyproject.org" in text:
        fatal.append(f":octagonal_sign: This is the training website's URL. {please}")

    if "galaxy" not in text:
        if not ('/u/' in text and ('/h/' in text or '/w/' in text)):
            fatal.append(
                f":octagonal_sign: This does not include a galaxy shared history url. {please}"
            )

    if len(fatal) > 0:
        return (warnings, fatal)

    urls = re.findall(r"https?://[^\s]+", text)
    print(f"urls: {urls}")

    for url in urls:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                warnings.append(f":warning: This url was not 200 OK. #{url}")
            if "galaxy" not in resp.text:
                warnings.append(
                    f":warning: This url doesn't look like a Galaxy URL. #{url}"
                )
        except requests.ReadTimeout:
            warnings.append(
                ":warning: We could not access this URL before it timed out."
            )
    return (warnings, fatal)


def parse_time(timestr):
    return isodate.parse_duration(f'PT{timestr}'.upper())

def get_course_name_and_time(module):
    (type, key) = module.split(':', 1)
    key2 = "" + key
    if key2.endswith('/tutorial'):
        key2 = key2[0:len(key2) - len('/tutorial')]
    if key2.endswith('/slides'):
        key2 = key2[0:len(key2) - len('/slides')]

    # Fix up a couple of bad keys.
    if 'admin/connect-to-compute-cluster/combined' == key:
        key = 'admin/connect-to-compute-cluster'
    elif 'admin/object-store/exercise' == key:
        key = 'admin/object-store'

    if type == 'session':
        sum_study = timedelta(seconds=0)
        for sk in sessions[key]['videos']:
            sk2 = "" + sk
            if sk2.endswith('/tutorial'):
                sk2 = sk2[:len(sk2) - len('/tutorial')]
            if sk2.endswith('/slides'):
                sk2 = sk2[:len(sk2) - len('/slides')]

            sum_study += parse_time(studyloaddata.get(key, studyloaddata.get(sk2, "00M")))

        return (sessions[key].get('title', key), sum_study)
    elif type == 'video':
        possible_titles = [
            videos.get(key, {}).get('title', None),
            gtndata.get(key, None),
            videos.get(key2, {}).get('title', None),
            gtndata.get(key2, None)
        ]
        possible_titles = list(set([x for x in possible_titles if x is not None]))
        possible_study = [
            studyloaddata.get(key, None),
            studyloaddata.get(key2, None),
        ]
        possible_study = list(set([x for x in possible_study if x is not None]))

        if len(possible_titles) == 0:
            raise Exception(f"Fix {key} / {key2}")
        return (possible_titles[0], parse_time(possible_study[0] if len(possible_study) > 0 else '15m'))
    elif type == 'channel':
        if key in ('galaxy-intro', 'galaxy-intro2'):
            return ("Intro to Galaxy", parse_time('2H'))
        elif key == 'general':
            return ("General Galaxy Skills Module", parse_time('2H'))
        else:
            raise Exception(f"Unknown module {module}")
    else:
        raise Exception(f"Unknown module {module}")


def addCertificateRequest(user_id, human_name):
    # Save to DB
    existing_requests = CertificateRequest.objects.filter(
        slack_user_id=user_id,
    )
    if len(existing_requests) == 0:
        q = CertificateRequest(
            slack_user_id=user_id,
            human_name=human_name,
            course="GTN Smörgåsbord 3",
            approved="UNK",
        )
        q.save()
    else:
        existing_requests[0].human_name = human_name
        existing_requests[0].save()

# Match all the ways users screw up the /completed command:
# / completed
# \completed
# completed /
# completed/
# ... /completed
BAD_COMPLETED = re.compile(r"(^`/completed|^ /completed|/ completed|\\completed|completed\s*/|^completed|[^/]completed\s+|^.+/completed|/<[^>]*\|completed>)")
