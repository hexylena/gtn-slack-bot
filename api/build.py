#!/usr/bin/env python
import os
import pytz
import argparse
from datetime import datetime, timedelta
from pytz import timezone
import pytz
from api.models import ScheduledMessage

TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'messages')

replacements = {
    'Pacific/Auckland': {
        'REGION': 'Asia/Pacific :earth_asia:',
        'BYE_REGION': 'Americas :earth_americas:'
    },
    'Europe/Amsterdam': {
        'REGION': 'Africa/Middle East/Europe :earth_africa:',
        'BYE_REGION': 'Asia/Pacific :earth_asia:'
    },
    'America/New_York': {
        'REGION': 'Americas :earth_americas:',
        'BYE_REGION': 'Europe/Middle East/Africa :earth_africa:'
    },
    #'gat': {
    #    'SOCIAL_CHANNEL': '#event-gat',
    #    'EVENT': 'GTN Tapas: Galaxy Admin Training',
    #    'COURSE_WEBSITE': 'https://gallantries.github.io/video-library/events/smorgasbord2/gat.html',
    #},
    'gtn': {
        'SOCIAL_CHANNEL': '#social',
        'EVENT': 'GTN Smörgåsbord 3',
        'COURSE_WEBSITE': 'https://gallantries.github.io/video-library/events/smorgasbord3/',
        'GCC_CTA': 'https://galaxyproject.org/events/gcc2023/',
        'COC': 'https://gxy.io/coc'
    }
}


def template_messages(channel_id=None, zones=None, start=None, days=5, dry_run=True,
                      **kwargs):
    course = 'gtn'
    zones = [timezone(x) for x in zones]
    # Meh, lazy
    earliest_zone = zones[0]
    print(channel_id, zones, start, days, dry_run)

    if days > 2:
        posts = []

        for tz in zones:
            posts.append(
                (f'welcome-{course}.md', start, tz),
            )

        for tz in zones:
            for i in range(1, days - 1):
                posts.append(
                    (f'shift-change-{i}-{course}.md', start + timedelta(days=i, hours=2), tz)
                )

        for tz in zones:
            posts.append(
                # Sent in evening
                (f'goodbye-{course}.md', start + timedelta(days=days - 1, hours=4), tz)
            )
    else:
        posts = []

        for tz in zones:
            posts.append(
                (f'welcome-{course}.md', start, tz),
            )


    for post in posts:
        fn, time, tz = post
        localised_time = tz.localize(time)
        print(tz, time, localised_time, fn)

        with open(os.path.join(TEMPLATES, fn), 'r') as handle:
            data = handle.read()

        for k, v in replacements[str(tz)].items():
            data = data.replace(f'<{k}>', v)

        print(kwargs)
        for k, v in replacements[course].items():
            data = data.replace(f'<{k.upper()}>', v)

        if dry_run:
            print(f"Creating ScheduledMessage for {channel_id} {localised_time}")
            print(data)
            continue

        ScheduledMessage.objects.create(
            slack_channel_id=channel_id,
            message=data,
            scheduled_for=localised_time,
        )
