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
        module='account_invoice_discount_global', type_='model')
    Pool.register(
        invoice.Purchase,
        depends=['purchase'],
        module='account_invoice_discount_global', type_='model')
    Pool.register(
        invoice.Sale,
        depends=['sale'],
        module='account_invoice_discount_global', type_='model')
