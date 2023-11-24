# coding: utf-8
import xppy

xppy.set_cmd('/usr/bin')    # Change this to xppaut in your path

def run_xpp_ode(ode_file):

    print('Simulating %s with XPPAUT'% ode_file)
    subHopf=xppy.run(ode_file)
    subHopf.getDesc()
    sHData=subHopf.getRawData()
    sHData.shape
    from xppy.utils import plot
    plot.plotLC(subHopf.getRawData())
    plot.pl.show()


if __name__ == "__main__":

    import sys
    ode_file = sys.argv[1] if len(sys.argv)>1 else 'examples/nca.ode'

    run_xpp_ode(ode_file)


