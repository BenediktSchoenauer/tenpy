"""A collection of tests for :module:`tenpy.networks.mps`.

"""
# Copyright 2018 TeNPy Developers

import numpy as np
import numpy.testing as npt
from tenpy.models.xxz_chain import XXZChain
from tenpy.models.lattice import Square

from tenpy.networks import mps, site
from random_test import rand_permutation, random_MPS
import tenpy.linalg.np_conserved as npc

from nose.plugins.attrib import attr

spin_half = site.SpinHalfSite(conserve='Sz')


def test_mps():
    site_triv = site.SpinHalfSite(conserve=None)
    psi = mps.MPS.from_product_state([site_triv] * 4, [0, 1, 0, 1], bc='finite')
    psi.test_sanity()
    for L in [4, 2, 1]:
        print(L)
        state = (spin_half.state_indices(['up', 'down']) * L)[:L]
        psi = mps.MPS.from_product_state([spin_half] * L, state, bc='finite')
        psi.test_sanity()
        print(repr(psi))
        print(str(psi))
        psi2 = psi.copy()
        ov = psi.overlap(psi2)
        assert (abs(ov - 1.) < 1.e-15)
        if L > 1:
            npt.assert_equal(psi.entanglement_entropy(), 0.)  # product state has no entanglement.
        E = psi.expectation_value('Sz')
        npt.assert_array_almost_equal_nulp(E, ([0.5, -0.5] * L)[:L], 100)
        C = psi.correlation_function('Sz', 'Sz')
        npt.assert_array_almost_equal_nulp(C, np.outer(E, E), 100)
        norm_err = psi.norm_test()
        assert (np.linalg.norm(norm_err) < 1.e-13)


def test_mps_add():
    s = site.SpinHalfSite(conserve='Sz')
    u, d = 'up', 'down'
    psi1 = mps.MPS.from_product_state([s] * 4, [u, u, d, u], bc='finite')
    psi2 = mps.MPS.from_product_state([s] * 4, [u, d, u, u], bc='finite')
    psi_sum = psi1.add(psi2, 0.5**0.5, -0.5**0.5)
    npt.assert_almost_equal(psi_sum.norm, 1.)
    npt.assert_almost_equal(psi_sum.overlap(psi1), 0.5**0.5)
    npt.assert_almost_equal(psi_sum.overlap(psi2), -0.5**0.5)
    # check overlap with singlet state
    psi = mps.MPS.from_singlets(s, 4, [(1, 2)], lonely=[0, 3], up=u, down=d, bc='finite')
    #  ov = psi.overlap(psi_sum.copy())
    print("total charge psi1", psi1.get_total_charge())
    print("total charge psi2", psi2.get_total_charge())
    print("total charge psi_sum", psi_sum.get_total_charge())
    print("total charge psi", psi.get_total_charge())
    npt.assert_almost_equal(psi_sum.overlap(psi), 1.)

    psi2_prime = mps.MPS.from_product_state([s] * 4, [u, u, u, u], bc='finite')
    psi2_prime.apply_local_op(1, 'Sm', False, False)
    #  # now psi2_prime is psi2 up to gauging of charges.
    #  # can MPS.add handle this?
    psi_sum_prime = psi1.add(psi2_prime, 0.5**0.5, -0.5**0.5)
    npt.assert_almost_equal(psi_sum_prime.overlap(psi), 1.)


def test_MPSEnvironment():
    xxz_pars = dict(L=4, Jxx=1., Jz=1.1, hz=0.1, bc_MPS='finite')
    L = xxz_pars['L']
    M = XXZChain(xxz_pars)
    state = ([0, 1] * L)[:L]  # Neel state
    psi = mps.MPS.from_product_state(M.lat.mps_sites(), state, bc='finite')
    env = mps.MPSEnvironment(psi, psi)
    env.get_LP(3, True)
    env.get_RP(0, True)
    env.test_sanity()
    for i in range(4):
        ov = env.full_contraction(i)  # should be one
        print("total contraction on site", i, ": ov = 1. - ", ov - 1.)
        assert (abs(abs(ov) - 1.) < 1.e-14)
    env.expectation_value('Sz')


def test_singlet_mps():
    u, d = 'up', 'down'
    pairs = [(0, 3), (1, 6), (2, 5)]
    bond_singlets = np.array([1, 2, 3, 2, 2, 1, 0])
    lonely = [4, 7]
    L = 2 * len(pairs) + len(lonely)
    print("singlet pairs: ", pairs)
    print("lonely sites: ", lonely)
    psi = mps.MPS.from_singlets(spin_half, L, pairs, lonely=lonely, lonely_state=u, bc='finite')
    psi.test_sanity()
    print('chi = ', psi.chi)
    assert (np.all(2**bond_singlets == np.array(psi.chi)))
    ent = psi.entanglement_entropy() / np.log(2)
    npt.assert_array_almost_equal_nulp(ent, bond_singlets, 5)
    psi.entanglement_spectrum(True)  # (just check that the function runs)
    npt.assert_almost_equal(psi.norm, 1.)
    npt.assert_almost_equal(psi.overlap(psi), 1.)
    id_vals = psi.expectation_value("Id")
    npt.assert_almost_equal(id_vals, [1.]*L)
    Sz_vals = psi.expectation_value("Sigmaz")
    expected_Sz_vals = [(0. if i not in lonely else 1.) for i in range(L)]
    print("Sz_vals = ", Sz_vals)
    print("expected_Sz_vals = ", expected_Sz_vals)
    npt.assert_almost_equal(Sz_vals, expected_Sz_vals)
    ent_segm = psi.entanglement_entropy_segment(list(range(4))) / np.log(2)
    print(ent_segm)
    npt.assert_array_almost_equal_nulp(ent_segm, [2, 3, 1, 3, 2], 5)
    coord, mutinf = psi.mutinf_two_site()
    coord = [(i, j) for i, j in coord]
    mutinf[np.abs(mutinf) < 1.e-14] = 0.
    mutinf /= np.log(2)
    print(mutinf)
    for (i, j) in pairs:
        k = coord.index((i, j))
        mutinf[k] -= 2.  # S(i)+S(j)-S(ij) = (1+1-0)*log(2)
    npt.assert_array_almost_equal(mutinf, 0., decimal=14)
    product_state = [None]*L
    for i, j in pairs:
        product_state[i] = u
        product_state[j] = d
    for k in lonely:
        product_state[k] = u
    psi2 = mps.MPS.from_product_state([spin_half]*L, product_state, bc='finite')
    npt.assert_almost_equal(psi.overlap(psi2), 0.5**(0.5*len(pairs)))


def test_charge_fluctuations():
    L = 6
    pairs = [(0, 3), (2, 4)]
    lonely = [1, 5]
    psi = mps.MPS.from_singlets(spin_half, L, pairs, lonely=lonely, lonely_state='up',
                                bc='segment')
    # mps not yet gauged to zero qtotal!
    average_charge = np.array([psi.average_charge(b) for b in range(psi.L+1)]).T
    charge_variance = np.array([psi.charge_variance(b) for b in range(psi.L+1)]).T
    print(average_charge)
    print(charge_variance)
    npt.assert_array_almost_equal(average_charge, [[0., 0., 0., 0., 0., 0., 0.]], decimal=14)
    npt.assert_array_almost_equal(charge_variance, [[ 0.,  1.,  1.,  2.,  1.,  0.,  0.]],
                                  decimal=14)

    # now gauge to zero qtotal
    psi.gauge_total_charge()
    average_charge = np.array([psi.average_charge(b) for b in range(psi.L+1)]).T
    charge_variance = np.array([psi.charge_variance(b) for b in range(psi.L+1)]).T
    print(average_charge)
    print(charge_variance)
    npt.assert_array_almost_equal(average_charge, [[0., 0., 1., 1., 1., 1., 2.]], decimal=14)
    npt.assert_array_almost_equal(charge_variance, [[ 0.,  1.,  1.,  2.,  1.,  0.,  0.]],
                                  decimal=14)


def test_mps_swap():
    L = 6
    pairs = [(0, 3), (1, 5), (2, 4)]
    pairs_swap = [(0, 2), (1, 5), (3, 4)]
    print("singlet pairs: ", pairs)
    psi = mps.MPS.from_singlets(spin_half, L, pairs, bc='finite')
    psi_swap = mps.MPS.from_singlets(spin_half, L, pairs_swap, bc='finite')
    psi.swap_sites(2)
    assert abs(psi.overlap(psi_swap) - 1.) < 1.e-15
    # now test permutation
    # recover original psi
    psi = mps.MPS.from_singlets(spin_half, L, pairs, bc='finite')
    perm = rand_permutation(L)
    pairs_perm = [(perm[i], perm[j]) for i, j in pairs]
    psi_perm = mps.MPS.from_singlets(spin_half, L, pairs_perm, bc='finite')
    psi.permute_sites(perm, verbose=2)
    print(psi.overlap(psi_perm), psi.norm_test())
    assert abs(abs(psi.overlap(psi_perm)) - 1.) < 1.e-10


def test_TransferMatrix(chi=4, d=2):
    psi = random_MPS(2, d, chi, bc='infinite', form=None)
    full_TM = npc.tensordot(psi._B[0], psi._B[0].conj(), axes=['p', 'p*'])
    full_TM = npc.tensordot(full_TM, psi._B[1], axes=['vR', 'vL'])
    full_TM = npc.tensordot(full_TM, psi._B[1].conj(), axes=[['vR*', 'p'], ['vL*', 'p*']])
    full_TM = full_TM.combine_legs([['vL', 'vL*'], ['vR', 'vR*']], qconj=[+1, -1])
    full_TM_dense = full_TM.to_ndarray()
    eta_full, w_full = np.linalg.eig(full_TM_dense)
    sort = np.argsort(np.abs(eta_full))[::-1]
    eta_full = eta_full[sort]
    w_full = w_full[:, sort]
    TM = mps.TransferMatrix(psi, psi, charge_sector=0, form=None)
    eta, w = TM.eigenvectors(3)
    print("transfer matrix yields eigenvalues ", eta)
    print(eta.shape, eta_full.shape)
    print(psi.dtype)
    # note: second and third eigenvalue are complex conjugates
    if bool(eta[2].imag > 0.) == bool(eta_full[2].imag > 0.):
        npt.assert_allclose(eta[:3], eta_full[:3])
    else:
        npt.assert_allclose(eta[:3], eta_full[:3].conj())
    # compare largest eigenvector
    w0_full = w_full[:, 0]
    w0 = w[0].to_ndarray()
    assert (abs(np.sum(w0_full)) > 1.e-20)  # should be the case for random stuff
    w0_full /= np.sum(w0_full)  # fixes norm & phase
    w0 /= np.sum(w0)
    npt.assert_allclose(w0, w0_full)


def test_compute_K():
    pairs = [(0, 1), (2, 3), (4, 5)]  # singlets on a 3x2 grid -> k_y = pi
    psi = mps.MPS.from_singlets(spin_half, 6, pairs, bc='infinite')
    psi.test_sanity()
    lat = Square(3, 2, spin_half, order='default', bc_MPS='infinite', bc='periodic')
    U, W, q, ov, te = psi.compute_K(lat, verbose=100)
    assert (ov == -1.)
    npt.assert_array_equal(W, [1.])


def check_canonical_form(bc):
    psi = random_MPS(8, 2, 6, form=None, bc=bc)
    psi2 = psi.copy()
    norm = np.sqrt(psi2.overlap(psi2, ignore_form=True))
    print("norm =", norm)
    psi2.norm /= norm  # normalize psi2
    norm2 = psi.overlap(psi2, ignore_form=True)
    print("norm2 =", norm2)
    assert abs(norm2 - norm) < 1.e-14 * norm
    psi.canonical_form(renormalize=False)
    psi.test_sanity()
    assert abs(psi.norm - norm) < 1.e-14 * norm
    psi.norm = 1.  # normalized psi
    ov = psi.overlap(psi2, ignore_form=True)
    print("normalized states: overlap <psi_canonical|psi> = 1.-", 1. - ov)
    assert abs(ov - 1.) < 1.e-14
    print("norm_test")
    print(psi.norm_test())
    assert np.max(psi.norm_test()) < 1.e-14


@attr('slow')
def test_canonical_form():
    yield check_canonical_form, 'finite'
    yield check_canonical_form, 'infinite'


def test_group():
    s = site.SpinHalfSite(conserve='parity')
    psi1 = mps.MPS.from_singlets(s, 6, [(1, 3), (2, 5)], lonely=[0, 4], bc='finite')
    psi2 = psi1.copy()
    print("group n=2")
    psi2.group_sites(n=2)
    assert psi2.L == psi1.L//2
    psi2.test_sanity()
    psi2.group_split()
    psi2.test_sanity()
    ov = psi1.overlap(psi2)
    assert abs(1.-ov) < 1.e-14
    psi4 = psi1.copy()
    print("group n=4")
    psi4.group_sites(n=4)
    psi4.test_sanity()
    psi4.group_split()
    psi4.test_sanity()
    ov = psi1.overlap(psi4)
    assert abs(1.-ov) < 1.e-14


def test_expectation_value_term():
    s = spin_half
    psi1 = mps.MPS.from_singlets(s, 6, [(1, 3), (2, 5)], lonely=[0, 4], bc='finite')
    ev = psi1.expectation_value_term([('Sz', 2), ('Sz', 3)])
    assert abs(0.-ev) < 1.e-14
    ev = psi1.expectation_value_term([('Sz', 1), ('Sz', 3)])
    assert abs(-0.25-ev) < 1.e-14
    ev = psi1.expectation_value_term([('Sz', 3), ('Sz', 1), ('Sz', 4)])
    assert abs(-0.25*0.5-ev) < 1.e-14
    fs = site.SpinHalfFermionSite()
    # check fermionic signs
    psi2 = mps.MPS.from_product_state([fs]*4, ['empty', 'up', 'down', 'full'], bc="infinite")
    ev = psi2.expectation_value_term([('Cu', 2), ('Nu', 1), ('Cdu', 2)])
    assert 1. == ev
    ev2 = psi2.expectation_value_term([('Cu', 2), ('Cd', 1), ('Cdd', 1), ('Cdu', 2)])
    assert ev2 == ev
    ev3 = psi2.expectation_value_term([('Cd', 1), ('Cu', 2), ('Cdd', 1), ('Cdu', 2)])
    assert ev3 == -ev2
    # over the infinite MPS boundary
    ev = psi2.expectation_value_term([('Nu', 1), ('Nd', 4)]) # should be zero
    assert abs(ev) == 0.
    ev = psi2.expectation_value_term([('Nu', 1), ('Nd', 6)]) # should be zero
    assert abs(ev) == 1.
    # terms_sum
    pref = np.random.random([5])
    evsum, _ = psi2.expectation_value_terms_sum([[('Nd', 0)],
                                                 [('Nu', 1), ('Nd', 2)],
                                                 [('Nd', 2), ('Nu', 5)],
                                                 [('Nu Nd', 3)],
                                                 [('Nu', 1), ('Nu', 5)]], # yapf: disable
                                                pref) # should be zero
    assert abs(evsum) == sum(pref[1:])


def test_onsite_terms():
    L = 6
    strength1 = np.arange(1., 1.+L*0.25, 0.25)
    o1 = mps.OnsiteTerms(L)
    for i in [1, 0, 3]:
        o1.add_onsite_term(strength1[i], i, "X_{i:d}".format(i=i))
    assert o1.onsite_terms == [{"X_0": strength1[0]},
                               {"X_1": strength1[1]},
                               {},
                               {"X_3": strength1[3]},
                               {},
                               {}] # yapf: disable
    strength2 = np.arange(2., 2.+L*0.25, 0.25)
    o2 = mps.OnsiteTerms(L)
    for i in [1, 4, 3, 5]:
        o2.add_onsite_term(strength2[i], i, "Y_{i:d}".format(i=i))
    o2.add_onsite_term(strength2[3], 3, "X_3")  # add to previous part
    o2.add_onsite_term(-strength1[1], 1, "X_1")  # remove previous part
    o1 += o2
    assert o1.onsite_terms == [{"X_0": strength1[0]},
                               {"X_1": 0., "Y_1": strength2[1]},
                               {},
                               {"X_3": strength1[3] + strength2[3], "Y_3": strength2[3]},
                               {"Y_4": strength2[4]},
                               {"Y_5": strength2[5]}] # yapf: disable
    o1.remove_zeros()
    assert o1.onsite_terms == [{"X_0": strength1[0]},
                               {"Y_1": strength2[1]},
                               {},
                               {"X_3": strength1[3]+ strength2[3], "Y_3": strength2[3]},
                               {"Y_4": strength2[4]},
                               {"Y_5": strength2[5]}] # yapf: disable

def test_coupling_terms():
    L = 4
    sites = []
    for i in range(L):
        s = site.Site(spin_half.leg)
        s.add_op("X_{i:d}".format(i=i), 2.*np.eye(2))
        s.add_op("Y_{i:d}".format(i=i), 3.*np.eye(2))
        sites.append(s)
    strength1 = np.arange(0., 5)[:, np.newaxis] + np.arange(0., 0.625, 0.125)[np.newaxis, :]
    c1 = mps.CouplingTerms(L)
    for i, j in [(2, 3)]:
        c1.add_coupling_term(strength1[i, j], i, j, "X_{i:d}".format(i=i), "Y_{j:d}".format(j=j))
    assert c1.max_range() == 3 - 2
    for i, j in [(0, 1), (0, 3), (0, 2)]:
        c1.add_coupling_term(strength1[i, j], i, j, "X_{i:d}".format(i=i), "Y_{j:d}".format(j=j))
    c1_des = {0: {('X_0', 'Id'): {1: {'Y_1': 0.125},
                                  2: {'Y_2': 0.25},
                                  3: {'Y_3': 0.375}}},
              2: {('X_2', 'Id'): {3: {'Y_3': 2.375}}}} # yapf: disable
    assert c1.coupling_terms == c1_des
    c1._test_terms(sites)
    assert c1.max_range() == 3 - 0
    mc = mps.MultiCouplingTerms(L)
    for i, j in [(2, 3)]:  # exact same terms as c1
        mc.add_coupling_term(strength1[i, j], i, j, "X_{i:d}".format(i=i), "Y_{j:d}".format(j=j))
    assert mc.max_range() == 3 - 2
    for i, j in [(0, 1), (0, 3), (0, 2)]:  # exact same terms as c1
        mc.add_coupling_term(strength1[i, j], i, j, "X_{i:d}".format(i=i), "Y_{j:d}".format(j=j))
    assert mc.coupling_terms == c1_des
    assert mc.max_range() == 3 - 0
    mc.add_multi_coupling_term(20., [0, 1, 3], ['X_0', 'Y_1', 'Y_3'], ['Id', 'Id'])
    mc.add_multi_coupling_term(30., [0, 1, 3], ['X_0', 'Y_1', 'Y_3'], ['S1', 'S2'])
    mc.add_multi_coupling_term(40., [1, 2, 3], ['X_1', 'Y_2', 'Y_3'], ['Id', 'Id'])
    mc_des = {0: {('X_0', 'Id'): {1: {'Y_1': 0.125,
                                      ('Y_1', 'Id'): {3: {'Y_3': 20.0}}},
                                  2: {'Y_2': 0.25},
                                  3: {'Y_3': 0.375}},
                  ('X_0', 'S1'): {1: {('Y_1', 'S2'): {3: {'Y_3': 30.0}}}}},
              1: {('X_1', 'Id'): {2: {('Y_2', 'Id'): {3: {'Y_3': 40.0}}}}},
              2: {('X_2', 'Id'): {3: {'Y_3': 2.375}}}} # yapf: disable
    assert mc.coupling_terms == mc_des
    mc._test_terms(sites)
    # addition
    c2 = mps.CouplingTerms(L)
    for i, j in [(0, 1), (1, 2)]:
        c1.add_coupling_term(strength1[i, j], i, j, "X_{i:d}".format(i=i), "Y_{j:d}".format(j=j))
    c1 += c2
    c1_des = {0: {('X_0', 'Id'): {1: {'Y_1': 0.25},
                                  2: {'Y_2': 0.25},
                                  3: {'Y_3': 0.375}}},
              1: {('X_1', 'Id'): {2: {'Y_2': 1.25}}},
              2: {('X_2', 'Id'): {3: {'Y_3': 2.375}}}} # yapf: disable
    assert c1.coupling_terms == c1_des
    c1._test_terms(sites)
    mc += c1
    mc_des = {0: {('X_0', 'Id'): {1: {'Y_1': 0.375,
                                      ('Y_1', 'Id'): {3: {'Y_3': 20.0}}},
                                  2: {'Y_2': 0.5},
                                  3: {'Y_3': 0.75}},
                  ('X_0', 'S1'): {1: {('Y_1', 'S2'): {3: {'Y_3': 30.0}}}}},
              1: {('X_1', 'Id'): {2: {'Y_2': 1.25,
                                      ('Y_2', 'Id'): {3: {'Y_3': 40.0}}}}},
              2: {('X_2', 'Id'): {3: {'Y_3': 4.75}}}} # yapf: disable
    assert mc.coupling_terms == mc_des
    # coupling accross mps boundary
    mc.add_multi_coupling_term(50., [1, 3, 5], ['X_1', 'Y_3', 'Y_1'], ['JW', 'STR'])
    assert mc.max_range() == 5 - 1
    mc._test_terms(sites)
    # remove the last coupling again
    mc.add_multi_coupling_term(-50., [1, 3, 5], ['X_1', 'Y_3', 'Y_1'], ['JW', 'STR'])
    mc.remove_zeros()
    assert mc.coupling_terms == mc_des
    assert mc.max_range() == 3 - 0


if __name__ == "__main__":
    test_charge_fluctuations()
    test_mps()
    test_mps_add()
    test_MPSEnvironment()
    test_singlet_mps()
    test_TransferMatrix()
    test_compute_K()
    check_canonical_form('finite')
    check_canonical_form('infinite')
    test_group()
    test_expectation_value_term()
    test_coupling_terms()
