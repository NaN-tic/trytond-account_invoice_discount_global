================================
Invoice Discount Global Scenario
================================

Imports::

    >>> import datetime
    >>> from decimal import Decimal
    >>> from proteus import Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences, create_payment_term
    >>> today = datetime.date.today()

Install account_invoice_discount_global::

    >>> config = activate_modules('account_invoice_discount_global')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')
    >>> period = fiscalyear.periods[0]

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> receivable = accounts['receivable']
    >>> payable = accounts['payable']
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> account_tax = accounts['tax']
    >>> account_cash = accounts['cash']

Create tax::

    >>> Tax = Model.get('account.tax')
    >>> tax = create_tax(Decimal('.10'))
    >>> tax.save()

Create party with customer invoice discount of 5% and supplier discount of 3%::

    >>> Party = Model.get('party.party')
    >>> party = Party(name='Party')
    >>> party.customer_invoice_discount = Decimal('0.05')
    >>> party.supplier_invoice_discount = Decimal('0.03')
    >>> party.save()

Create account category::

    >>> ProductCategory = Model.get('product.category')
    >>> account_category = ProductCategory(name="Account Category")
    >>> account_category.accounting = True
    >>> account_category.account_expense = expense
    >>> account_category.account_revenue = revenue
    >>> account_category.customer_taxes.append(tax)
    >>> account_category.supplier_taxes.append(Tax(tax.id))
    >>> account_category.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.default_uom = unit
    >>> template.type = 'service'
    >>> template.list_price = Decimal('40')
    >>> template.account_category = account_category
    >>> template.save()
    >>> product, = template.products

Create discount product::

    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.default_uom = unit
    >>> template.type = 'service'
    >>> template.list_price = Decimal('0')
    >>> template.cost_price = Decimal('0')
    >>> template.account_category = account_category
    >>> template.save()
    >>> discount_product, = template.products

Configure discount product::

    >>> Configuration = Model.get('account.configuration')
    >>> configuration = Configuration(1)
    >>> configuration.discount_product = discount_product
    >>> configuration.save()

Create payment term::

    >>> payment_term = create_payment_term()
    >>> payment_term.save()

Create customer invoice::

    >>> Invoice = Model.get('account.invoice')
    >>> invoice = Invoice()
    >>> invoice.party = party
    >>> invoice.payment_term = payment_term
    >>> invoice.invoice_date = today
    >>> line1 = invoice.lines.new()
    >>> line1.product = product
    >>> line1.quantity = 5
    >>> line1.unit_price = Decimal('40')
    >>> line2 = invoice.lines.new()
    >>> line2.account = revenue
    >>> line2.description = 'Test'
    >>> line2.quantity = 1
    >>> line2.unit_price = Decimal('20')
    >>> invoice.untaxed_amount
    Decimal('220.00')
    >>> invoice.tax_amount
    Decimal('20.00')
    >>> invoice.total_amount
    Decimal('240.00')
    >>> invoice.save()

Check invoice discount is party's customer invoice discount::

    >>> invoice.invoice_discount
    Decimal('0.05')

Change invoice discount::

    >>> invoice.invoice_discount = Decimal('0.1')
    >>> invoice.untaxed_amount
    Decimal('220.00')
    >>> invoice.save()

Post invoice and check discount is applied::

    >>> invoice.click('validate_invoice')
    >>> invoice.state
    'validated'
    >>> invoice.click('post')
    >>> invoice.state
    'posted'
    >>> invoice.invoice_discount
    Decimal('0.1')
    >>> discount_line, = [l for l in invoice.lines
    ...     if l.product == discount_product]
    >>> discount_line.quantity
    1.0
    >>> discount_line.amount
    Decimal('-22.00')
    >>> invoice.untaxed_amount
    Decimal('198.00')
    >>> invoice.tax_amount
    Decimal('17.80')
    >>> invoice.total_amount
    Decimal('215.80')

Credit invoice with refund::

    >>> credit = Wizard('account.invoice.credit', [invoice])
    >>> credit.form.with_refund = True
    >>> credit.execute('credit')
    >>> invoice.reload()
    >>> invoice.state
    'cancelled'
    >>> credit_note, = Invoice.find([('untaxed_amount', '<', Decimal(0))])
    >>> credit_note.untaxed_amount
    Decimal('-198.00')

Duplicate invoice::

    >>> duplicate, = invoice.duplicate()
    >>> duplicate.click('post')
    >>> duplicate.untaxed_amount
    Decimal('198.00')

Create supplier invoice::

    >>> invoice = Invoice()
    >>> invoice.type = 'in'
    >>> invoice.party = party
    >>> invoice.payment_term = payment_term
    >>> invoice.invoice_date = today
    >>> line = invoice.lines.new()
    >>> line.product = product
    >>> line.quantity = 10
    >>> line.unit_price = Decimal('25')
    >>> invoice.untaxed_amount
    Decimal('250.00')
    >>> invoice.tax_amount
    Decimal('25.00')
    >>> invoice.total_amount
    Decimal('275.00')
    >>> invoice.save()

Check invoice discount is parties supplier invoice discount::

    >>> invoice.invoice_discount
    Decimal('0.03')

Post invoice and check discount is applied::

    >>> invoice.click('validate_invoice')
    >>> invoice.state
    'validated'
    >>> invoice.click('post')
    >>> invoice.state
    'posted'
    >>> invoice.invoice_discount
    Decimal('0.03')
    >>> discount_line, = [l for l in invoice.lines
    ...     if l.product == discount_product]
    >>> discount_line.quantity
    1.0
    >>> discount_line.amount
    Decimal('-7.50')
    >>> invoice.untaxed_amount
    Decimal('242.50')
    >>> invoice.tax_amount
    Decimal('24.25')
    >>> invoice.total_amount
    Decimal('266.75')
