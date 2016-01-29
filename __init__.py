# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .invoice import *
from .party import *

def register():
    Pool.register(
        Party,
        Configuration,
        Invoice,
        InvoiceLine,
        Sale,
        module='account_invoice_discount_global', type_='model')
