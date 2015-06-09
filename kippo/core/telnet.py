from twisted.internet import protocol
from twisted.manhole import telnet
from twisted.conch import recvline
from twisted.conch.telnet import TelnetTransport, TelnetBootstrapProtocol, TelnetProtocol
from twisted.conch.insults import insults

from kippo.core.protocol import HoneyPotInteractiveProtocol, LoggingServerProtocol
from kippo.core.ssh import HoneyPotAvatar
from kippo.core.honeypot import HoneyPotEnvironment, HoneyPotShell

class TelnetShell(recvline.HistoricRecvLine):
    """Simple echo protocol.

    Accepts lines of input and writes them back to its connection.  If
    a line consisting solely of \"quit\" is received, the connection
    is dropped.
    """
    
    def __init__(self, *args, **kwargs):
        env = HoneyPotEnvironment()
        user = HoneyPotAvatar("root", env)
        
        self.honeypot = HoneyPotInteractiveProtocol(user, env)
        self.shell = None
        pass

    def lineReceived(self, line):
        if not self.shell:
            self.honeypot.terminal = self.terminal
            self.shell = HoneyPotShell(self.honeypot)
        
        self.shell.lineReceived(line)

class HoneyPotTelnetFactory(protocol.ServerFactory):
    def __init__(self):
        self.protocol = lambda: TelnetTransport(TelnetBootstrapProtocol,
                                             insults.ServerProtocol,
                                             TelnetShell,
                                             #telnetShellArg,
                                             #telnetShellKWArg="zxcv"
                                             )

#env = HoneyPotEnvironment()
#user = HoneyPotAvatar("root", env)