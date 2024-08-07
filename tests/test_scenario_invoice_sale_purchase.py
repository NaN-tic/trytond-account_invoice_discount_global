import datetime
import unittest
from decimal import Decimal

from proteus import Model
from trytond.modules.account.tests.tools import (create_chart,
                                                 create_fiscalyear, create_tax,
                                                 get_accounts)
from trytond.modules.account_invoice.tests.tools import (
    create_payment_term, set_fiscalyear_invoice_sequences)
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        # Install account_invoice_discount_global, sale and purchase
        config = activate_modules(
            ['account_invoice_discount_global', 'sale', 'purchase'])

        # Create company
        _ = create_company()
        company = get_company()

        # Create fiscal year
        fiscalyear = set_fiscalyear_invoice_sequences(
            create_fiscalyear(company))
        fiscalyear.click('create_period')

        # Create chart of accounts
        _ = create_chart(company)
        accounts = get_accounts(company)
        revenue = accounts['revenue']
        expense = accounts['expense']

        # Create tax
        Tax = Model.get('account.tax')
        tax = create_tax(Decimal('.10'))
        tax.save()

        # Create parties
        Party = Model.get('party.party')
        supplier = Party(name='Supplier')
        supplier.supplier_invoice_discount = Decimal('0.03')
        supplier.save()
        customer = Party(name='Customer')
        customer.customer_invoice_discount = Decimal('0.05')
        customer.save()

        # Create account category
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name="Account Category")
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.customer_taxes.append(tax)
        account_category.supplier_taxes.append(Tax(tax.id))
        account_category.save()

        # Create product
        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        template = ProductTemplate()
        template.name = 'product'
        template.default_uom = unit
        template.type = 'service'
        template.purchasable = True
        template.salable = True
        template.list_price = Decimal('40')
        template.account_category = account_category
        template.save()
        product, = template.products
        product.cost_price = Decimal('25')
        product.save()

        # Create discount product
        template = ProductTemplate()
        template.name = 'product'
        template.default_uom = unit
        template.type = 'service'
        template.list_price = Decimal('0')
        template.account_category = account_category
        template.save()
        discount_product, = template.products

        # Configure discount product
        Configuration = Model.get('account.configuration')
        configuration = Configuration(1)
        configuration.discount_product = discount_product
        configuration.save()

        # Create payment term
        payment_term = create_payment_term()
        payment_term.save()

        # Sale 5 services
        Sale = Model.get('sale.sale')
        SaleLine = Model.get('sale.line')
        sale = Sale()
        sale.party = customer
        sale.payment_term = payment_term
        sale.invoice_method = 'order'
        sale_line = SaleLine()
        sale.lines.append(sale_line)
        sale_line.product = product
        sale_line.quantity = 5.0
        sale.save()
        Sale.quote([sale.id], config.context)
        Sale.confirm([sale.id], config.context)
        Sale.process([sale.id], config.context)
        self.assertEqual(sale.state, 'processing')
        sale.reload()
        self.assertEqual(sale.untaxed_amount, Decimal('200.00'))
        self.assertEqual(sale.tax_amount, Decimal('20.00'))
        self.assertEqual(sale.total_amount, Decimal('220.00'))
        self.assertEqual(len(sale.shipments), 0)

        self.assertEqual(len(sale.shipment_returns), 0)

        self.assertEqual(len(sale.invoices), 1)
        invoice, = sale.invoices
        self.assertEqual(invoice.origins, sale.rec_name)

        # Created invoice has customer's invoice discount
        self.assertEqual(invoice.invoice_discount, Decimal('0.05'))

        # Post invoice and check discount is applied
        Invoice = Model.get('account.invoice')
        Invoice.post([i.id for i in sale.invoices], config.context)
        invoice.reload()
        discount_line, = [
            l for l in invoice.lines if l.product == discount_product
        ]
        self.assertEqual(discount_line.quantity, 1.0)
        self.assertEqual(discount_line.amount, Decimal('-10.00'))
        self.assertEqual(invoice.untaxed_amount, Decimal('190.00'))
        self.assertEqual(invoice.tax_amount, Decimal('19.00'))
        self.assertEqual(invoice.total_amount, Decimal('209.00'))

        # Purchase 3 services
        Purchase = Model.get('purchase.purchase')
        purchase = Purchase()
        purchase.party = supplier
        purchase.payment_term = payment_term
        purchase.invoice_method = 'order'
        purchase_line = purchase.lines.new()
        purchase_line.product = product
        purchase_line.quantity = 3.0
        purchase_line.unit_price = product.cost_price
        purchase.click('quote')
        purchase.click('confirm')
        purchase.click('process')
        self.assertEqual(purchase.state, 'processing')
        purchase.reload()
        self.assertEqual(purchase.untaxed_amount, Decimal('75.00'))
        self.assertEqual(purchase.tax_amount, Decimal('7.50'))
        self.assertEqual(purchase.total_amount, Decimal('82.50'))
        self.assertEqual(len(purchase.moves), 0)

        self.assertEqual(len(purchase.shipment_returns), 0)

        self.assertEqual(len(purchase.invoices), 1)
        invoice, = purchase.invoices
        self.assertEqual(invoice.origins, purchase.rec_name)

        # Created invoice has supplier's invoice discount
        self.assertEqual(invoice.invoice_discount, Decimal('0.03'))

        # Post invoice and check discount is applied
        today = datetime.date.today()
        invoice.invoice_date = today
        invoice.save()
        Invoice.post([invoice.id], config.context)
        invoice.reload()
        discount_line, = [
            l for l in invoice.lines if l.product == discount_product
        ]
        self.assertEqual(discount_line.quantity, 1.0)
        self.assertEqual(discount_line.amount, Decimal('-2.25'))
        self.assertEqual(invoice.untaxed_amount, Decimal('72.75'))
        self.assertEqual(invoice.tax_amount, Decimal('7.28'))
        self.assertEqual(invoice.total_amount, Decimal('80.03'))
