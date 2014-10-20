# -*- coding: utf-8 -*-
"""
    __init__.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import Pool
from carrier import Carrier
from sale import Sale
from shipment import ShipmentOut


def register():
    Pool.register(
        Sale,
        ShipmentOut,
        Carrier,
        module='carrier_pricelist', type_='model'
    )
