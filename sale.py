# -*- coding: utf-8 -*-
"""
    sale.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from decimal import Decimal

from trytond.transaction import Transaction
from trytond.pool import PoolMeta, Pool

__metaclass__ = PoolMeta
__all__ = ['Sale']


class Sale:
    __name__ = "sale.sale"

    def _get_carrier_context(self):
        "Pass sale in the context"
        context = super(Sale, self)._get_carrier_context()

        if self.carrier.carrier_cost_method != 'pricelist':
            return context

        context = context.copy()
        context['sale'] = self.id
        return context

    def update_pricelist_shipment_cost(self):
        "Add a shipping line to sale for pricelist costmethod"
        Sale = Pool().get('sale.sale')
        Currency = Pool().get('currency.currency')

        if not self.carrier or self.carrier.carrier_cost_method != 'pricelist':
            return

        with Transaction().set_context(self._get_carrier_context()):
            shipment_cost = self.carrier.get_sale_price()
        if not shipment_cost[0]:
            return

        shipment_cost = Currency.compute(
            Currency(shipment_cost[1]), shipment_cost[0], self.currency
        )
        Sale.write([self], {
            'lines': [
                ('create', [{
                    'type': 'line',
                    'product': self.carrier.carrier_product.id,
                    'description': self.carrier.carrier_product.name,
                    'quantity': 1,  # XXX
                    'unit': self.carrier.carrier_product.sale_uom.id,
                    'unit_price': Decimal(shipment_cost),
                    'shipment_cost': Decimal(shipment_cost),
                    'amount': Decimal(shipment_cost),
                    'taxes': [],
                    'sequence': 9999,  # XXX
                }]),
                ('delete', [
                    line for line in self.lines if line.shipment_cost
                ]),
            ]
        })

    @classmethod
    def quote(cls, sales):
        res = super(Sale, cls).quote(sales)

        for sale in sales:
            sale.update_pricelist_shipment_cost()
        return res
