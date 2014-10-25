# -*- coding: utf-8 -*-
"""
    tests/test_carrier.py

    :copyright: (C) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import sys
import os
DIR = os.path.abspath(os.path.normpath(os.path.join(
    __file__, '..', '..', '..', '..', '..', 'trytond'
)))
if os.path.isdir(DIR):
    sys.path.insert(0, os.path.dirname(DIR))
import unittest
import datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta
if 'DB_NAME' not in os.environ:
    from trytond.config import CONFIG
    CONFIG['db_type'] = 'sqlite'
    os.environ['DB_NAME'] = ':memory:'

import pycountry

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, USER, DB_NAME, CONTEXT
from trytond.transaction import Transaction


class CarrierTestCase(unittest.TestCase):

    def setUp(self):
        """
        Set up data used in the tests.
        this method is called before each test function execution.
        """
        trytond.tests.test_tryton.install_module('carrier_pricelist')

        self.Currency = POOL.get('currency.currency')
        self.Company = POOL.get('company.company')
        self.Party = POOL.get('party.party')
        self.User = POOL.get('res.user')
        self.ProductTemplate = POOL.get('product.template')
        self.Uom = POOL.get('product.uom')
        self.ProductCategory = POOL.get('product.category')
        self.Product = POOL.get('product.product')
        self.Country = POOL.get('country.country')
        self.Subdivision = POOL.get('country.subdivision')
        self.Employee = POOL.get('company.employee')
        self.Carrier = POOL.get('carrier')
        self.PriceList = POOL.get('product.price_list')
        self.Sale = POOL.get('sale.sale')

    def _create_fiscal_year(self, date=None, company=None):
        """
        Creates a fiscal year and requried sequences
        """
        FiscalYear = POOL.get('account.fiscalyear')
        Sequence = POOL.get('ir.sequence')
        SequenceStrict = POOL.get('ir.sequence.strict')
        Company = POOL.get('company.company')

        if date is None:
            date = datetime.date.today()

        if company is None:
            company, = Company.search([], limit=1)

        invoice_sequence, = SequenceStrict.create([{
            'name': '%s' % date.year,
            'code': 'account.invoice',
            'company': company,
        }])
        fiscal_year, = FiscalYear.create([{
            'name': '%s' % date.year,
            'start_date': date + relativedelta(month=1, day=1),
            'end_date': date + relativedelta(month=12, day=31),
            'company': company,
            'post_move_sequence': Sequence.create([{
                'name': '%s' % date.year,
                'code': 'account.move',
                'company': company,
            }])[0],
            'out_invoice_sequence': invoice_sequence,
            'in_invoice_sequence': invoice_sequence,
            'out_credit_note_sequence': invoice_sequence,
            'in_credit_note_sequence': invoice_sequence,
        }])
        FiscalYear.create_period([fiscal_year])
        return fiscal_year

    def _create_coa_minimal(self, company):
        """Create a minimal chart of accounts
        """
        AccountTemplate = POOL.get('account.account.template')
        Account = POOL.get('account.account')

        account_create_chart = POOL.get(
            'account.create_chart', type="wizard")

        account_template, = AccountTemplate.search([('parent', '=', None)])

        session_id, _, _ = account_create_chart.create()
        create_chart = account_create_chart(session_id)
        create_chart.account.account_template = account_template
        create_chart.account.company = company
        create_chart.transition_create_account()

        receivable, = Account.search([
            ('kind', '=', 'receivable'),
            ('company', '=', company),
        ])
        payable, = Account.search([
            ('kind', '=', 'payable'),
            ('company', '=', company),
        ])
        create_chart.properties.company = company
        create_chart.properties.account_receivable = receivable
        create_chart.properties.account_payable = payable
        create_chart.transition_create_properties()

    def _get_account_by_kind(self, kind, company=None, silent=True):
        """Returns an account with given spec

        :param kind: receivable/payable/expense/revenue
        :param silent: dont raise error if account is not found
        """
        Account = POOL.get('account.account')
        Company = POOL.get('company.company')

        if company is None:
            company, = Company.search([], limit=1)

        accounts = Account.search([
            ('kind', '=', kind),
            ('company', '=', company)
        ], limit=1)
        if not accounts and not silent:
            raise Exception("Account not found")
        return accounts[0] if accounts else False

    def _create_payment_term(self):
        """Create a simple payment term with all advance
        """
        PaymentTerm = POOL.get('account.invoice.payment_term')

        return PaymentTerm.create([{
            'name': 'Direct',
            'lines': [('create', [{'type': 'remainder'}])]
        }])

    def _create_countries(self, count=5):
        """
        Create some sample countries and subdivisions
        """
        for country in list(pycountry.countries)[0:count]:
            countries = self.Country.create([{
                'name': country.name,
                'code': country.alpha2,
            }])
            try:
                divisions = pycountry.subdivisions.get(
                    country_code=country.alpha2
                )
            except KeyError:
                pass
            else:
                for subdivision in list(divisions)[0:count]:
                    self.Subdivision.create([{
                        'country': countries[0].id,
                        'name': subdivision.name,
                        'code': subdivision.code,
                        'type': subdivision.type.lower(),
                    }])

    def setup_defaults(self):
        """Creates default data for testing
        """
        self.currency, = self.Currency.create([{
            'name': 'US Dollar',
            'code': 'USD',
            'symbol': '$',
        }])

        with Transaction().set_context(company=None):
            company_party, = self.Party.create([{
                'name': 'openlabs'
            }])
            employee_party, = self.Party.create([{
                'name': 'Jim'
            }])

        self.company, = self.Company.create([{
            'party': company_party,
            'currency': self.currency,
        }])

        self.employee, = self.Employee.create([{
            'party': employee_party.id,
            'company': self.company.id,
        }])

        self.User.write([self.User(USER)], {
            'company': self.company,
            'main_company': self.company,
            'employees': [('add', [self.employee.id])],
        })
        # Write employee separately as employees needs to be saved first
        self.User.write([self.User(USER)], {
            'employee': self.employee.id,
        })

        CONTEXT.update(self.User.get_preferences(context_only=True))

        # Create Fiscal Year
        self._create_fiscal_year(company=self.company.id)
        # Create Chart of Accounts
        self._create_coa_minimal(company=self.company.id)
        # Create a payment term
        self.payment_term, = self._create_payment_term()

        # Create carrier
        carrier_price_list, = self.PriceList.create([{
            'name': 'PL 1',
            'company': self.company.id,
            'lines': [
                ('create', [{
                    'formula': '(unit_price * 0.0) + 5',
                }])
            ],
        }])
        carrier_party, = self.Party.create([{
            'name': 'Pricelist Carrier',
        }])

        day, = self.Uom.search([('name', '=', 'Day')])
        carrier_product_template, = self.ProductTemplate.create([{
            'name': 'Carrier Pricelist',
            'type': 'service',
            'salable': True,
            'default_uom': day.id,
            'sale_uom': day.id,
            'account_revenue': self._get_account_by_kind('revenue').id,
            'list_price': Decimal('50'),
            'cost_price': Decimal('40'),
        }])
        carrier_product, = self.Product.create([{
            'template': carrier_product_template.id,
        }])
        self.carrier, = self.Carrier.create([{
            'party': carrier_party.id,
            'carrier_cost_method': 'pricelist',
            'carrier_product': carrier_product.id,
            'price_list': carrier_price_list.id,
        }])

        unit, = self.Uom.search([('name', '=', 'Unit')])

        self.template1, = self.ProductTemplate.create([{
            'name': 'Product 1',
            'type': 'goods',
            'salable': True,
            'default_uom': unit.id,
            'sale_uom': unit.id,
            'list_price': Decimal('100'),
            'cost_price': Decimal('90'),
            'account_revenue': self._get_account_by_kind('revenue').id,
            'products': [('create', [{
                'code': 'product-1'
            }])]
        }])

        self.template2, = self.ProductTemplate.create([{
            'name': 'Product 2',
            'type': 'goods',
            'salable': True,
            'default_uom': unit.id,
            'sale_uom': unit.id,
            'list_price': Decimal('50'),
            'cost_price': Decimal('40'),
            'account_revenue': self._get_account_by_kind('revenue').id,
            'products': [('create', [{
                'code': 'product-1'
            }])]
        }])

        self.product1 = self.template1.products[0]
        self.product2 = self.template2.products[0]

        # Create sale party
        self.sale_party, = self.Party.create([{
            'name': 'Test Sale Party',
            'addresses': [('create', [{
                'name': 'John Doe',
                'street': '123 Main Street',
                'zip': '83702',
                'city': 'Boise',
            }])]
        }])

    def test_0010_test_shipping_price(self):
        """Test shipping price
        """
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()

            # Create sale order
            sale, = self.Sale.create([{
                'reference': 'S-1001',
                'company': self.company,
                'currency': self.currency,
                'payment_term': self.payment_term,
                'party': self.sale_party.id,
                'invoice_address': self.sale_party.addresses[0].id,
                'shipment_address': self.sale_party.addresses[0].id,
                'carrier': self.carrier.id,
                'lines': [
                    ('create', [{
                        'type': 'line',
                        'quantity': 2,
                        'product': self.product1,
                        'unit_price': Decimal('100.00'),
                        'description': 'Test Description1',
                        'unit': self.product1.template.default_uom,
                    }, {
                        'type': 'line',
                        'quantity': 2,
                        'product': self.product2,
                        'unit_price': Decimal('50.00'),
                        'description': 'Test Description2',
                        'unit': self.product2.template.default_uom,
                    }]),
                ]
            }])

            self.assertEqual(sale.total_amount, Decimal('300'))

            with Transaction().set_context(company=self.company.id):
                # Quote the sale
                self.Sale.quote([sale])
                self.Sale.confirm([sale])
                self.Sale.process([sale])

            # Shipping line is added and total amount got updated.
            self.assertEqual(len(sale.lines), 3)
            self.assertEqual(sale.total_amount, Decimal('320'))

            self.assertEqual(len(sale.shipments), 1)

            shipment, = sale.shipments
            self.assertEqual(shipment.cost, Decimal(20))


def suite():
    """
    Define suite
    """
    test_suite = trytond.tests.test_tryton.suite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(CarrierTestCase)
    )
    return test_suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
