# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
from trytond.model import ModelView, Workflow, fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval
from trytond.i18n import gettext
from trytond.exceptions import UserError
from trytond.modules.product import price_digits, round_price

__all__ = ['Configuration', 'Invoice', 'InvoiceLine', 'Sale', 'Purchase']


class Configuration(metaclass=PoolMeta):
    __name__ = 'account.configuration'
    discount_product = fields.Many2One('product.product', 'Discount Product')


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'
    invoice_discount = fields.Numeric('Invoice Discount',
        digits=price_digits, states={
            'readonly': Eval('state') != 'draft',
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
    def compute_discount_global(cls, invoices):
        Line = Pool().get('account.invoice.line')

        lines = []
        to_update = []
        for invoice in invoices:
            if not invoice.invoice_discount:
                continue
            discount_line = invoice._get_discount_global_line()
            if discount_line:
                lines.append(discount_line)
                to_update.append(invoice)

        if lines:
            Line.create([x._save_values() for x in lines])
        cls.update_taxes(to_update)

    def _get_discount_global_line(self):
        pool = Pool()
        Config = pool.get('account.configuration')
        Line = pool.get('account.invoice.line')

        config = Config(1)
        product = config.discount_product
        if not product:
            raise UserError(gettext(
                'account_invoice_discount_global.msg_missing_discount_product',
                name=self.rec_name,
                ))

        # check invoice has a global discount line; not create a new line
        for line in self.lines:
            if (line.type == 'line' and line.product
                    and line.product.id == product.id):
                return

        amount = -1 * self.untaxed_amount * self.invoice_discount
        if amount:
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
            line.unit_price = round_price(amount)
            line.sequence = 9999
            line._update_taxes(self.type, self.party)
            return line

    @classmethod
    def remove_discount_global(cls, invoices):
        pool = Pool()
        Line = pool.get('account.invoice.line')
        Config = pool.get('account.configuration')

        config = Config(1)
        product = config.discount_product
        if not product:
            return

        to_delete = []
        to_update_taxes = []
        for invoice in invoices:
            if invoice.state in ('cancelled', 'posted', 'paid'):
                continue
            for line in invoice.lines:
                if (line.type == 'line' and line.product
                        and line.product.id == product.id):
                    to_delete.append(line)
                    to_update_taxes.append(invoice)
                    break

        if to_delete:
            Line.delete(to_delete)
        if to_update_taxes:
            cls.update_taxes(to_update_taxes)

    def _credit(self, **values):
        credit = super(Invoice, self)._credit(**values)
        credit.invoice_discount = self.invoice_discount
        return credit

    @classmethod
    @ModelView.button
    @Workflow.transition('validated')
    def validate_invoice(cls, invoices):
        cls.compute_discount_global(invoices)
        super(Invoice, cls).validate_invoice(invoices)

    @classmethod
    @ModelView.button
    @Workflow.transition('posted')
    def post(cls, invoices):
        cls.compute_discount_global(invoices)
        super(Invoice, cls).post(invoices)

    @classmethod
    @ModelView.button
    @Workflow.transition('draft')
    def draft(cls, invoices):
        super(Invoice, cls).draft(invoices)
        cls.remove_discount_global(invoices)

    @classmethod
    @ModelView.button
    @Workflow.transition('cancelled')
    def cancel(cls, invoices):
        super(Invoice, cls).cancel(invoices)
        cls.remove_discount_global(invoices)


class InvoiceLine(metaclass=PoolMeta):
    __name__ = 'account.invoice.line'

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


class Sale(metaclass=PoolMeta):
    __name__ = 'sale.sale'

    def _get_invoice(self):
        invoice = super(Sale, self)._get_invoice()
        if invoice:
            invoice.invoice_discount = (
                invoice.on_change_with_invoice_discount())
        return invoice


class Purchase(metaclass=PoolMeta):
    __name__ = 'purchase.purchase'

    def _get_invoice(self):
        invoice = super(Purchase, self)._get_invoice()
        if invoice:
            invoice.invoice_discount = (
                invoice.on_change_with_invoice_discount())
        return invoice
