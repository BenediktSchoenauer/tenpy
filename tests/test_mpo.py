"""A collection of tests for (classes in) :module:`tenpy.networks.mpo`.

.. todo ::
    A lot more to test...
"""

from __future__ import division

import numpy as np
import numpy.testing as npt
import nose.tools as nst

from tenpy.linalg import np_conserved as npc

from tenpy.networks import mpo, site

site_spin_half = site.spin_half_site(conserve='Sz')


def test_MPO():
    s = site_spin_half
    for bc in mpo.MPO._valid_bc:
        for L in [4, 2, 1]:
            print bc, ", L =", L
            grid = [[s.Id, s.Sp, s.Sz], [None, None, s.Sm], [None, None, s.Id]]
            legW = npc.LegCharge.from_qflat(s.leg.chinfo, [[0], s.Sp.qtotal, [0]])
            W = npc.grid_outer(grid, [legW, legW.conj()])
            W.set_leg_labels(['wL', 'wR', 'p', 'p*'])
            Ws = [W]*L
            if bc == 'finite':
                Ws[0] = Ws[0][0:1, :, :, :]
                Ws[-1] = Ws[-1][:, 2:3, :, :]
            H = mpo.MPO([site_spin_half]*L, Ws, bc=bc, IdL=[0]*L+[None], IdR=[None] +[-1]*(L))
            print H.dim
            print H.chi


def test_MPOGraph():
    for bc in mpo.MPO._valid_bc:
        for L in [4, 2, 1]:  # TODO: also 1?
            print "L =", L
            g = mpo.MPOGraph([site_spin_half]*L, 'finite')
            g.test_sanity()
            g.add(0, 'IdL', 'Sz0', 'Sz', 1.)
            if L > 1:
                g.add(1, 'Sz0', 'IdR', 'Sz', 0.5)
            g.add_missing_IdL_IdR()
            print repr(g)
            print str(g)
            g_mpo = g.build_MPO()
            g_mpo.test_sanity()