# coding: utf-8
import xppy
xppy.set_cmd('/usr/bin')       # Change this to xppaut in your path
subHopf=xppy.run('examples/nca.ode')
subHopf.getDesc()
sHData=subHopf.getRawData()
sHData.shape
from xppy.utils import plot
plot.plotLC(subHopf.getRawData())
plot.pl.show()
