#!bin/python

"""
play sounds according to POST requests. cooperate with pubsubhubbub
"""
import web, sys, jsonlib, subprocess, os
import speechd.client

sensorWords = {"wifi" : "why fi",
               "bluetooth" : "bluetooth"}

def aplay(device, filename):
    paDeviceName = {
        'garage' : 'alsa_output.pci-0000_01_07.0.analog-stereo',
        'living' : 'alsa_output.pci-0000_00_04.0.analog-stereo',
        }[device]
    subprocess.call(['paplay', '-d', paDeviceName, filename])

def soundOut(preSound=None, speech=None, postSound=None):
    if preSound:
        aplay('living', preSound)

    def playPost(action):
        if action == 'end':
            if postSound is not None:
                aplay('living', postSound)

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

class index(object):
    def GET(self):
        web.header('Content-type', 'text/html')
        return '''
<p><form action="speak" method="post">say: <input type="text" name="say"> <input type="submit"></form></p>
<p><form action="testSound" method="post"> <input type="submit" value="test sound"></form></p>
'''

class speak(object):
    def POST(self):
        speechClient.speak(web.input()['say'])
        return "sent"

class testSound(object):
    def POST(self):
        soundOut(preSound='/my/music/entrance/leave.wav')
        return 'ok'

urls = (
    r'/', 'index',
    r'/speak', 'speak',
    r'/testSound', 'testSound',
    r'/visitorNet', 'visitorNet',
    )

app = web.application(urls, globals(), autoreload=True)

speechClient = speechd.client.Speaker("websound")

if __name__ == '__main__':
    sys.argv.append("9049")
    app.run()
