#!bin/python
import re, ast, restkit, time, jsonlib, logging, traceback, datetime, optparse
from dateutil import tz
from rdflib import Literal, Variable
from pymongo import Connection
log = logging.getLogger()
logging.basicConfig(level=logging.INFO)

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

        m = re.match(r"http://(.*?):(.*?)@(.*)", url)   
        r = restkit.Resource('http://%s' % m.group(3))
        r.add_authorization(restkit.httpc.BasicAuth((m.group(1), m.group(2))))
        routers.append(r)
    return routers, knownMacAddr

def getPresentMacAddrs(routers):
    addrs = [] # (addr, signalStrength)
    for router in routers:
        log.debug("GET %s", router)
        data = router.get()
        for _, mac, signal in jsValue(data, 'wldev'):
            addrs.append((mac, signal))
    return addrs


parser = optparse.OptionParser()
parser.add_option("-v", action="store_true")
opts, args = parser.parse_args()
if opts.v:
    log.setLevel(logging.DEBUG)

routers, knownMacAddr = routerEndpoints()
getName = lambda mac: knownMacAddr.get(mac, 'unknown %s' % mac)
mongo = Connection('bang', 27017)['visitor']['visitor']

lastSeenMac = set()
hub = restkit.Resource(
    # PSHB not working yet; "http://bang:9030/"
    "http://slash:9049/"
    )

def sendMsg(msg):
    """adds created time, writes mongo and hub"""
    log.info(str(msg))
    hub.post("visitorNet", payload=jsonlib.dumps(msg))
    msg['created'] = datetime.datetime.now(tz.gettz('UTC'))
    mongo.save(msg)
    
while True:
    try:
        newMac = set()
        log.debug("scan")
        for mac, signal in getPresentMacAddrs(routers):
            newMac.add(mac)
        for mac in newMac.difference(lastSeenMac):
            sendMsg({"arrive" : getName(mac)})
        for mac in lastSeenMac.difference(newMac):
            sendMsg({"leave" : getName(mac)})

        lastSeenMac = newMac
    except Exception, e:
        traceback.print_exc()
    time.sleep(5)

    
