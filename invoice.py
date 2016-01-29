from decimal import Decimal
from trytond.model import ModelView, Workflow, fields
from trytond.pool import PoolMeta, Pool
from trytond.config import config
from trytond.pyson import Eval

__all__ = ['Configuration', 'Invoice', 'InvoiceLine', 'Sale']

DISCOUNT_DIGITS = int(config.get('digits', 'discount_digits', 4))


class Configuration:
    __name__ = 'account.configuration'
    __metaclass__ = PoolMeta
    discount_product = fields.Many2One('product.product', 'Discount Product')


class Invoice:
    __name__ = 'account.invoice'
    __metaclass__ = PoolMeta
    invoice_discount = fields.Numeric('Invoice Discount',
        digits=(16, DISCOUNT_DIGITS), states={
            'readonly': Eval('state') != 'draft',
            'invisible': Eval('type').in_(['in_invoice', 'in_credit_note']),
            }, depends=['state'])

    @classmethod
    def __setup__(cls):
        super(Invoice, cls).__setup__()
        cls._error_messages.update({
                'missing_discount_product': ('Invoice "%s" has a discount but '
                    'no discount product is configured.'),
                })

    @staticmethod
    def default_invoice_discount():
        return Decimal(0)

    @fields.depends('party')
    def on_change_with_invoice_discount(self):
        if self.party:
            return self.party.invoice_discount

    @classmethod
    @ModelView.button
    def compute_discount(cls, invoices):
        pool = Pool()
        Line = pool.get('account.invoice.line')
        Config = Pool().get('account.configuration')
        config = Config(1)
        product = config.discount_product
        lines = []
        for invoice in invoices:
            if not invoice.invoice_discount:
                continue
            lines.extend(invoice._get_discount_line(invoice, product))
        if lines:
            Line.create([x._save_values for x in lines])
        cls.update_taxes(invoices)

    def _get_discount_line(self, invoice, product):
        Line = Pool().get('account.invoice.line')
        amount = -1 * invoice.untaxed_amount * invoice.invoice_discount
        lines = []
        if amount and invoice.lines:
            if not product:
                self.raise_user_error('missing_discount_product',
                    invoice.rec_name)
            line = Line()
            line.invoice = self
            line.type = 'line'
            line.product = product
            line.account = product.account_revenue_used
            line.description = product.rec_name
            line.quantity = 1
            line.unit = product.default_uom
            line.unit_price = amount
            line._update_taxes()
            lines.append(line)
        return lines

    @classmethod
    def remove_discount(cls, invoices):
        pool = Pool()
        Line = pool.get('account.invoice.line')
        Config = pool.get('account.configuration')
        product = Config(1).discount_product

        to_delete = []
        for invoice in invoices:
            lines = list(invoice.lines)
            for line in invoice.lines:
                if line.product == product:
                    lines.remove(line)
                    to_delete.append(line)
            invoice.lines = lines
        
        Line.delete(to_delete)
        for invoice in invoices:
            invoice.save()

    @classmethod
    @ModelView.button
    @Workflow.transition('validated')
    def validate_invoice(cls, invoices):
        cls.compute_discount(invoices)
        super(Invoice, cls).validate_invoice(invoices)

    @classmethod
    @ModelView.button
    @Workflow.transition('posted')
    def post(cls, invoices):
        cls.compute_discount(invoices)
        super(Invoice, cls).post(invoices)

    @classmethod
    @ModelView.button
    @Workflow.transition('draft')
    def draft(cls, invoices):
        super(Invoice, cls).draft(invoices)
        cls.remove_discount(invoices)

    @classmethod
    @ModelView.button
    @Workflow.transition('cancel')
    def cancel(cls, invoices):
        super(Invoice, cls).cancel(invoices)
        cls.remove_discount(invoices)


class InvoiceLine:
    __name__ = 'account.invoice.line'
    __metaclass__ = PoolMeta

    def _update_taxes(self):
        Tax = Pool().get('account.tax')
        taxes = []
        party = self.invoice.party
        pattern = self._get_tax_rule_pattern()
        for tax in self.product.customer_taxes_used:
            if party.customer_tax_rule:
                tax_ids = party.customer_tax_rule.apply(tax, pattern)
                if tax_ids:
                    taxes.extend(tax_ids)
                continue
            taxes.append(tax.id)
        if party.customer_tax_rule:
            tax_ids = party.customer_tax_rule.apply(None, pattern)
            if tax_ids:
                taxes.extend(tax_ids)
        self.taxes = Tax.browse(taxes)


class Sale:
    __name__ = 'sale.sale'
    __metaclass__ = PoolMeta

    def _get_invoice_sale(self, invoice_type):
        invoice = super(Sale, self)._get_invoice_sale(invoice_type)
        if invoice:
            invoice.invoice_discount = invoice.on_change_with_invoice_discount()
        return invoice
