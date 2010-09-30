#!bin/python

"""
play sounds according to POST requests. cooperate with pubsubhubbub
"""
import web, sys, jsonlib, subprocess, os
import speechd.client

sensorWords = {"wifi" : "why fi",
               "bluetooth" : "bluetooth"}

def soundOut(preSound=None, speech=None, postSound=None):
    if preSound:
        subprocess.call(['aplay', preSound])

    def playPost(action):
        if action == 'end':
            if postSound is not None:
                subprocess.call(['aplay', postSound])

    if speech:
        try:
            speechClient.speak(speech, playPost)
        except speechd.client.SSIPCommunicationError, e:
            # fix this by getting restarted
            raise SystemExit(str(e))
    else:
        playPost('end')

#def soundOut(preSound=None, speech=None, postSound=None):
#    print vars()


class visitorNet(object):
    def POST(self):
        data = jsonlib.loads(web.data())

        if data.get('action') == 'arrive':
            
            snd = ('/my/music/entrance/%s.wav' %
                   data['name'].replace(' ', '_').replace(':', '_'))
            if not os.path.exists(snd):
                snd = None

            soundOut(speech="new %s: %s" % (sensorWords[data['sensor']],
                                            data['name']),
                     postSound=snd)
            return 'ok'

        if data.get('action') == 'leave':
            soundOut(preSound='/my/music/entrance/leave.wav',
                     speech="lost %s. %s" % (sensorWords[data['sensor']],
                                             data['name']))
            return 'ok'
        
        return "nothing to do"

urls = (
    r'/visitorNet', 'visitorNet',
    )

app = web.application(urls, globals(), autoreload=True)

speechClient = speechd.client.Speaker("websound")

if __name__ == '__main__':
    sys.argv.append("9049")
    app.run()
