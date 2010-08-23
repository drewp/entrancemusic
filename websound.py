#!bin/python

"""
play sounds according to POST requests. cooperate with pubsubhubbub
"""
import web, sys, jsonlib, subprocess, os

class visitorNet(object):
    def POST(self):
        data = jsonlib.loads(web.data())
        if data.get('action') == 'arrive':
            snd = ('/my/music/entrance/%s.wav' %
                   data['name'].replace(' ', '_').replace(':', '_'))
            if os.path.exists(snd):
                subprocess.call(['aplay', snd])
                return 'ok'
            else:
                return "no sound for %s" % snd
        if data.get('action') == 'leave':
            subprocess.call(['aplay', '/my/music/entrance/leave.wav'])
            return 'ok'
        return "nothing to do"

urls = (
    r'/visitorNet', 'visitorNet',
    )

app = web.application(urls, globals(), autoreload=True)

if __name__ == '__main__':
    sys.argv.append("9049")
    app.run()
