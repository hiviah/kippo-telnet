import ConfigParser

from twisted.internet import protocol
from twisted.manhole import telnet
from twisted.conch import recvline
from twisted.conch.telnet import TelnetTransport, TelnetBootstrapProtocol, TelnetProtocol
from twisted.conch.insults import insults
from twisted.conch.ssh import session
from twisted.python import log

from kippo.core.protocol import HoneyPotInteractiveProtocol, LoggingServerProtocol
from kippo.core.ssh import HoneyPotAvatar, HoneyPotSSHSession
from kippo.core.honeypot import HoneyPotEnvironment, HoneyPotShell
from kippo.core.config import config


#session - HoneyPotAvatar
#HoneyPotBaseProtocol.terminal - LoggingServerProtocol
#HoneyPotBaseProtocol.terminal.transport - SSHSessionProcessProtocol
#HoneyPotBaseProtocol.terminal.transport.session - HoneyPotSSHSession
#HoneyPotBaseProtocol.terminal.transport.session.conn - twisted.conch.ssh.connection.SSHConnection
#HoneyPotBaseProtocol.terminal.transport.session.conn.transport - HoneyPotTransport

class ConnectionWrapper(object):
    
    def __init__(self, transport):
        self.transport = transport
        
    
class TelnetShell(recvline.HistoricRecvLine):
    """Simple echo protocol.

    Accepts lines of input and writes them back to its connection.  If
    a line consisting solely of \"quit\" is received, the connection
    is dropped.
    """
    
    ps = ("root@svr03:/# ", "...")
    sessionCounter = 0
    
    def __init__(self, *args, **kwargs):
        env = HoneyPotEnvironment()
        user = HoneyPotAvatar("root", env)
        
        self.honeypot = HoneyPotInteractiveProtocol(user, env)
        self.shell = None
        pass

    def lineReceived(self, line):
        if not self.shell:
            session = HoneyPotSSHSession()
            self.terminal.transport.session = session
            self.terminal.transport.transport.sessionno = TelnetShell.sessionCounter #fffuuu almost global variable
            TelnetShell.sessionCounter += 1
            self.terminal.transport.session.conn = ConnectionWrapper(self.terminal.transport)
            self.honeypot.terminal = self.terminal
            self.shell = HoneyPotShell(self.honeypot)
        
        self.shell.lineReceived(line)

class HoneyPotTelnetFactory(protocol.ServerFactory):
    def __init__(self):
        #self.protocol = self.makeProtocol()
        cfg = config()
        
        self.protocol = lambda: TelnetTransport(TelnetBootstrapProtocol,
                                             insults.ServerProtocol,
                                             TelnetShell,
                                             #telnetShellArg,
                                             #telnetShellKWArg="zxcv"
                                             )
        self.dbloggers = []
        engine = 'mysql'
        
        dbengine = 'database_' + engine
        lcfg = ConfigParser.ConfigParser()
        lcfg.add_section(dbengine)
        for i in cfg.options(dbengine):
            lcfg.set(dbengine, i, cfg.get(dbengine, i))
        lcfg.add_section('honeypot')
        for i in cfg.options('honeypot'):
            lcfg.set('honeypot', i, cfg.get('honeypot', i))
        
        dbloggerModule = __import__(
            'kippo.dblog.%s' % (engine,),
            globals(), locals(), ['dblog']).dblog
        dblogger = dbloggerModule.mainLogger
        self.dbloggers.append(dblogger)
        
    def makeProtocol(self):
        env = HoneyPotEnvironment()
        user = HoneyPotAvatar("root", env)
        
        serverProtocol = insults.ServerProtocol(
            HoneyPotInteractiveProtocol, user, env)
        serverProtocol.makeConnection(protocol)
        protocol.makeConnection(session.wrapProtocol(serverProtocol))
        #honeypot = HoneyPotInteractiveProtocol(user, env)
        return serverProtocol
    
    def buildProtocol(self, addr):
        print 'New connection: %s:%s (%s:%s) [session: %d]' % \
            (addr.host, addr.port, "127.0.0.1", 6023, TelnetShell.sessionCounter)
        return protocol.ServerFactory.buildProtocol(self, addr)
        t = TelnetProtocol()
        #t.factory = self
        #return t
        
    def logDispatch(self, sessionid, msg):
        for dblog in self.dbloggers:
            dblog.logDispatch(sessionid, msg)

