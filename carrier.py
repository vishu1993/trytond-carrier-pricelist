# -*- coding: utf-8 -*-
"""
    carrier.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from decimal import Decimal

from trytond.transaction import Transaction
from trytond.exceptions import UserError
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
        """Estimates the shipment rate for the current shipment

        The get_sale_price implementation by tryton's carrier module
        returns a tuple of (value, currency_id)

        :returns: A tuple of (value, currency_id)
        """
        Sale = Pool().get('sale.sale')
        Shipment = Pool().get('stock.shipment.out')
        Company = Pool().get('company.company')

        shipment = Transaction().context.get('shipment')
        sale = Transaction().context.get('sale')

        company = Transaction().context.get('company')
        if not company:
            raise UserError("Company not in context.")

        default_currency = Company(company).currency

        if not sale and not shipment:
            return Decimal('0'), default_currency.id

        if self.carrier_cost_method != 'pricelist':
            return super(Carrier, self).get_sale_price()

        if sale:
            return Sale(sale).get_pricelist_shipping_cost()

        if shipment:
            return Shipment(shipment).get_pricelist_shipping_cost()

        return Decimal('0'), default_currency.id
