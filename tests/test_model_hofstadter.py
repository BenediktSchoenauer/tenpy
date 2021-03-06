# Copyright 2018 TeNPy Developers
from tenpy.models.hofstadter import HofstadterBosons
from test_model import check_general_model
from nose.plugins.attrib import attr


@attr('slow')
def test_HofstadterBosons():
    check_general_model(HofstadterBosons, {'Lx': 4}, {
        'conserve': [None, 'parity', 'N'],
        'U': [0., 0.123],
        'bc_MPS': ['finite', 'infinite']
    })
