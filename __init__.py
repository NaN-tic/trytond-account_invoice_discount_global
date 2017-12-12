# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import invoice
from . import party


def register():
    Pool.register(
        party.Party,
        party.PartyAccount,
        invoice.Configuration,
        invoice.Invoice,
        invoice.InvoiceLine,
        invoice.Purchase,
        invoice.Sale,
        module='account_invoice_discount_global', type_='model')
