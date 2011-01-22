#!bin/python
import re, ast, restkit, time, jsonlib, logging, traceback, datetime, optparse, socket
from dateutil import tz
from rdflib import Literal, Variable
from pymongo import Connection, DESCENDING
log = logging.getLogger()
logging.basicConfig(level=logging.INFO)
logging.getLogger('restkit.client').setLevel(logging.WARN)

def jsValue(js, variableName):
    # using literal_eval instead of json parser to handle the trailing commas
    val = re.search(variableName + r'\s*=\s*(.*?);', js, re.DOTALL).group(1)
    return ast.literal_eval(val)

def routerEndpoints():
    # ideally this would all be in the same rdf store, with int and
    # ext versions of urls
    
    txt = open("/my/site/magma/tomato_config.js").read().replace('\n', '')
    knownMacAddr = jsValue(txt, 'knownMacAddr')
    tomatoUrl = jsValue(txt, 'tomatoUrl')

    from rdflib.Graph import Graph
    g = Graph()
    g.parse("/my/proj/openid_proxy/access.n3", format="n3")
    repl = {'/tomato1/' : None, '/tomato2/' : None}
    for k in repl:
        rows = list(g.query('''
        PREFIX p: <http://bigasterisk.com/openid_proxy#>
        SELECT ?prefix WHERE {
          [
            p:requestPrefix ?public;
            p:proxyUrlPrefix ?prefix
            ]
        }''', initBindings={Variable("public") : Literal(k)}))
        repl[k] = str(rows[0][0])

    routers = []
    for url in tomatoUrl:
        for k, v in repl.items():
            url = url.replace(k, v)

        routers.append(restkit.Resource(url, timeout=2))
    return routers, knownMacAddr

def getPresentMacAddrs(routers):
    addrs = [] # (addr, signalStrength, name)
    macName = {}
    for router in routers:
        log.debug("GET %s", router)
        try:
            data = router.get().body_string()
        except socket.error:
            log.warn("get on %s failed" % router)
            continue
        for (name, ip, mac, lease) in jsValue(data, 'dhcpd_lease'):
            macName[mac] = name
        for _, mac, signal in jsValue(data, 'wldev'):
            addrs.append((mac, signal, macName.get(mac, None)))
    return addrs

parser = optparse.OptionParser()
parser.add_option("-v", action="store_true")
opts, args = parser.parse_args()
if opts.v:
    log.setLevel(logging.DEBUG)

routers, knownMacAddr = routerEndpoints()
mongo = Connection('bang', 27017)['visitor']['visitor']

def getName(mac, netName):
    return knownMacAddr.get(mac, netName or 'no name')


hub = restkit.Resource(
    # PSHB not working yet; "http://bang:9030/"
    "http://slash:9049/"
    )

def sendMsg(msg, hubPost=True):
    """adds created time, writes mongo and hub"""
    log.info(str(msg))
    if hubPost:
        hub.post("visitorNet", payload=jsonlib.dumps(msg))
    msg['created'] = datetime.datetime.now(tz.gettz('UTC'))
    mongo.save(msg)

def deltaSinceLastArrive(name):
    results = list(mongo.find({'name' : name}).sort('created', DESCENDING).limit(1))
    if not results:
        return datetime.timedelta.max
    now = datetime.datetime.now(tz.gettz('UTC'))
    last = results[0]['created'].replace(tzinfo=tz.gettz('UTC'))
    return now - last

class Poll(object):
    def __init__(self):
        self.lastSeenMac = set()

    def update(self):

        newMac = set()
        log.debug("scan")
        for mac, signal, name in getPresentMacAddrs(routers):
            newMac.add((mac, name))
        for mac, name in newMac.difference(self.lastSeenMac):
            dt = deltaSinceLastArrive(getName(mac, name))
            hubPost = dt > datetime.timedelta(hours=1)
            sendMsg({"sensor" : "wifi",
                     "address" : mac,
                     "name" : getName(mac, name),
                     "networkName" : name,
                     "action" : "arrive"},
                    hubPost=hubPost)
        for mac, name in self.lastSeenMac.difference(newMac):
            dt = deltaSinceLastArrive(getName(mac, name))
            hubPost = dt > datetime.timedelta(hours=1)           
            sendMsg({"sensor" : "wifi",
                     "address" : mac,
                     "name" : getName(mac, name),
                     "networkName" : name,
                     "action" : "leave"},
                    hubPost=hubPost)

        self.lastSeenMac = newMac
    

"""
todo: don't announce a drop and then a quick re-add. shorten
announcements of multiple devices on the same person showing up all
together.
"""
if __name__ == '__main__':
    poll = Poll()
    while True:
        try:
            poll.update()
        except Exception, e:
            traceback.print_exc()
        time.sleep(5)

    
