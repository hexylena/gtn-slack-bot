from django import forms
from django.utils import timezone


class ScheduleMessageForm(forms.Form):
    channel_id = forms.CharField(label="Slack Channel ID Or Name", max_length=100, initial="#testing", help_text="May be a #human label or a #C10293123 type label")
    start = forms.DateTimeField(help_text="When does the event start. This is (intentionally) a naïve datetime, and will be interpreted relative to each of the local time zones used (Pacific/Auckland, Europe/Amsterdam, Americas/New_York)")
    days = forms.IntegerField(initial=5, help_text="How long does the event last?")

    social_channel = forms.CharField(initial="#social", help_text="Where should people go to socialise?")
    event = forms.CharField(initial="GTN Smörgåsbord 3", help_text="Name of the event")
    website = forms.CharField(initial="https://gxy.io/smorgasbord3", help_text="Course website to link to")
    gcc_cta = forms.CharField(initial="https://galaxyproject.org/events/gcc2023/", help_text="A call to action included on 3-5 day events, for the current GCC")
    coc = forms.CharField(initial='https://gxy.io/coc', help_text="Link to event Code of Conduct")


class ScheduleMessageSingleForm(forms.Form):
    slack_channel_id = forms.CharField(label="Slack Channel ID Or Name", max_length=100, initial="#testing")
    message = forms.CharField(label="Message", initial="Hello, World", help_text="Message contents in GFM markdown", widget=forms.Textarea())
    scheduled_for = forms.DateTimeField(help_text="When should this message be sent out. Time is in UTC (server time), and the form defaults to the current time on page load.")
