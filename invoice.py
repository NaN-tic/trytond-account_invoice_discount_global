# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal

from trytond.config import config
from trytond.model import ModelView, Workflow, fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval

__all__ = ['Configuration', 'Invoice', 'InvoiceLine', 'Sale', 'Purchase']

DISCOUNT_DIGITS = (16, config.getint('product', 'price_decimal', default=4))


class Configuration:
    __name__ = 'account.configuration'
    __metaclass__ = PoolMeta
    discount_product = fields.Many2One('product.product', 'Discount Product')


class Invoice:
    __name__ = 'account.invoice'
    __metaclass__ = PoolMeta
    invoice_discount = fields.Numeric('Invoice Discount',
        digits=DISCOUNT_DIGITS, states={
            'readonly': Eval('state') != 'draft',
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

    @fields.depends('party', 'type')
    def on_change_with_invoice_discount(self):
        if self.party:
            if self.type == 'in':
                return self.party.supplier_invoice_discount
            else:
                return self.party.customer_invoice_discount

    @classmethod
    @ModelView.button
    def compute_discount(cls, invoices):
        pool = Pool()
        Line = pool.get('account.invoice.line')
        Config = Pool().get('account.configuration')

        product = Config(1).discount_product
        cls.remove_discount(invoices)
        lines = []
        for invoice in invoices:
            lines.extend(invoice._get_discount_line(product))
        if lines:
            Line.save(lines)
        cls.update_taxes(invoices)

    def _get_discount_line(self, product):
        Line = Pool().get('account.invoice.line')
        amount = -1 * self.untaxed_amount * (self.invoice_discount or 0)
        lines = []
        if amount:
            if not product:
                self.raise_user_error('missing_discount_product',
                    self.rec_name)
            line = Line()
            line.invoice = self
            line.type = 'line'
            line.product = product
            if self.type == 'in':
                line.account = product.account_expense_used
            else:
                line.account = product.account_revenue_used
            line.description = product.rec_name
            line.quantity = 1
            line.unit = product.default_uom
            line.unit_price = amount
            line._update_taxes(self.type, self.party)
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
            for line in invoice.lines:
                if line.product == product:
                    to_delete.append(line)
        Line.delete(to_delete)

    def _credit(self):
        credit = super(Invoice, self)._credit()
        credit.invoice_discount = self.invoice_discount
        return credit

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

    def _update_taxes(self, invoice_type, party):
        Tax = Pool().get('account.tax')
        taxes = []
        pattern = self._get_tax_rule_pattern()
        if invoice_type == 'in':
            for tax in self.product.supplier_taxes_used:
                if party.supplier_tax_rule:
                    tax_ids = party.supplier_tax_rule.apply(tax, pattern)
                    if tax_ids:
                        taxes.extend(tax_ids)
                    continue
                taxes.append(tax.id)
            if party.supplier_tax_rule:
                tax_ids = party.supplier_tax_rule.apply(None, pattern)
                if tax_ids:
                    taxes.extend(tax_ids)
        else:
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
        if taxes:
            self.taxes = Tax.browse(taxes)


class Sale:
    __name__ = 'sale.sale'
    __metaclass__ = PoolMeta

    def _get_invoice_sale(self):
        invoice = super(Sale, self)._get_invoice_sale()
        if invoice:
            invoice.invoice_discount = (
                invoice.on_change_with_invoice_discount())
        return invoice


class Purchase:
    __name__ = 'purchase.purchase'
    __metaclass__ = PoolMeta

    def _get_invoice_purchase(self):
        invoice = super(Purchase, self)._get_invoice_purchase()
        if invoice:
            invoice.invoice_discount = (
                invoice.on_change_with_invoice_discount())
        return invoice
