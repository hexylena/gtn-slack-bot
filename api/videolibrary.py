import os
import json


file_path = os.path.dirname(os.path.abspath(__file__))
videosjson = os.path.join(file_path, 'videos.json')
with open(videosjson, 'r') as handle:
    videos = json.load(handle)

sessionsjson = os.path.join(file_path, 'sessions.json')
with open(sessionsjson, 'r') as handle:
    sessions = json.load(handle)


def convert_name(path):
    path_parts = path.split('/')
    if path_parts[0] == 'statistics':
        path_parts[0] = 'machine_learning'
    if path_parts[0] == 'sequence-analysis':
        path_parts[0] = 'ngs'

    if 'galaxy/intro' in path or path_parts[0] == 'introduction':
        return 'galaxy-intro'
    elif path_parts[0] in ('galaxy', 'community', 'webinar'):
        return 'general'
    elif path_parts[0] == 'course':
        # These are specific to their events
        return '-'.join(['event', path_parts[1].replace('welcome-', '')])
    elif path_parts[0] == 'contributing':
        return 'gtn'
    elif 'tool-generators' in path_parts[1]:
        return 'dev-toolfactory'
    elif len(path_parts) > 2 and path_parts[2] in ('tutorial', 'slides'):
        return "_".join(path_parts[0:2])
    elif len(path_parts) > 2:
        return "_".join(path_parts[0:2])
    elif len(path_parts) == 2:
        return "_".join(path_parts[0:2])
    return None

INVERTED_SESSIONS = {}
for k, v in sessions.items():
    for vid in v['videos']:
        INVERTED_SESSIONS[vid] = k

CHANNEL_MAPPING = {}
for k, v in videos.items():
    if 'support_channel' in v:
        c = v['support_channel']
    else:
        c = convert_name(k)

    if c not in CHANNEL_MAPPING:
        CHANNEL_MAPPING[c] = []

    if k in INVERTED_SESSIONS:
        CHANNEL_MAPPING[c].append('session:' + INVERTED_SESSIONS[k])
    else:
        CHANNEL_MAPPING[c].append('video:' + k)

CHANNEL_MAPPING = {k: list(set(v)) for k, v in CHANNEL_MAPPING.items()}
