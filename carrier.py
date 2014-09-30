# -*- coding: utf-8 -*-
"""
    carrier.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.transaction import Transaction
from trytond.pool import PoolMeta, Pool
from trytond.model import fields
from trytond.pyson import Eval

__metaclass__ = PoolMeta
__all__ = ['Carrier']


class Carrier:
    __name__ = "carrier"

    price_list = fields.Many2One(
        "product.price_list", "Price List", states={
            "required": Eval("carrier_cost_method") == "pricelist",
            "invisible": Eval("carrier_cost_method") != "pricelist"
        }
    )

    @classmethod
    def __setup__(cls):
        super(Carrier, cls).__setup__()
        selection = ('pricelist', 'Price List')
        if selection not in cls.carrier_cost_method.selection:
            cls.carrier_cost_method.selection.append(selection)

    def get_rates(self):
        """Returns a list of tuple: (method, rate, currency, metadata)
        """
        Sale = Pool().get('sale.sale')

        sale = Transaction().context.get('sale')

        if not sale or self.carrier_cost_method != 'pricelist':
            return super(Carrier, self).get_rates()

        return Sale(sale).get_pricelist_shipping_rates()

    def get_sale_price(self):
        if self.carrier_cost_method != 'pricelist':
            return super(Carrier, self).get_sale_price()

        _, price, currency_id, _, _ = self.get_rates()[0]

        return price, currency_id
