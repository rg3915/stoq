# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2005, 2006 Async Open Source <http://www.async.com.br>
## All rights reserved
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU Lesser General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Lesser General Public License for more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., or visit: http://www.gnu.org/.
##
## Author(s):        Henrique Romano <henrique@async.com.br>
##
""" Create a simple sale to an example database"""

import sys
import datetime

from stoqlib.exceptions import SellError
from stoqlib.lib.defaults import INTERVALTYPE_MONTH
from stoqlib.lib.runtime import (new_transaction, print_msg,
                                 get_current_station, set_current_user)
from stoqlib.lib.parameters import sysparam
from stoqlib.lib.translation import stoqlib_gettext
from stoqlib.domain.examples.payment import MAX_INSTALLMENTS_NUMBER
from stoqlib.domain.till import get_current_till_operation, Till
from stoqlib.domain.sale import Sale
from stoqlib.domain.product import Product
from stoqlib.domain.person import Person
from stoqlib.domain.interfaces import (ISellable, IClient, IPaymentGroup,
                                       ISalesPerson, ICheckPM, IUser)

_ = stoqlib_gettext

# Number of installments for the sale
DEFAULT_PAYMENTS_NUMBER = 4

# Interval between payments (in days)
DEFAULT_PAYMENTS_INTERVAL = 30

# Number of sales to be created
DEFAULT_SALE_NUMBER = 4

DEFAULT_PAYMENT_INTERVAL_TYPE = INTERVALTYPE_MONTH
DEFAULT_PAYMENT_INTERVALS = 1

_till_operation = None

def get_till(conn):
    global _till_operation
    _till_operation = _till_operation or get_current_till_operation(conn)
    if _till_operation is None:
        _till_operation = Till(connection=conn,
                               station=get_current_station(conn))
        _till_operation.open_till()
    return _till_operation

def get_clients(conn):
    client_table = Person.getAdapterClass(IClient)
    result = client_table.select(connection=conn)
    if result.count() <= 0:
        raise SellError("You must have clients to create a sale!")
    return list(result)

def get_all_products(conn):
    result = Product.select(connection=conn)
    if result.count() <= 0:
        raise SellError("You have nothing to sale!")
        sys.exit()
    return list(result)

def _create_sale(conn, open_date, status, salesperson, client, coupon_id,
                 product, installments_number):
    sale = Sale(till=get_till(conn), client=client, status=status,
                open_date=open_date, coupon_id=coupon_id,
                salesperson=salesperson, cfop=sysparam(conn).DEFAULT_SALES_CFOP,
                connection=conn)
    sellable_facet = ISellable(product, connection=conn)
    sellable_facet.add_sellable_item(sale=sale)
    sale_total = sellable_facet.base_sellable_info.price
    # Sale's payments
    pg_facet = sale.addFacet(IPaymentGroup, connection=conn,
                             installments_number=DEFAULT_PAYMENTS_NUMBER)
    if installments_number > MAX_INSTALLMENTS_NUMBER:
        raise ValueError("Number of installments for this payment method can "
                         "not be greater than %d, got %d"
                         % (MAX_INSTALLMENTS_NUMBER, installments_number))
    check_method = ICheckPM(sysparam(conn).BASE_PAYMENT_METHOD,
                            connection=conn)
    check_method.setup_inpayments(pg_facet, installments_number,
                                  open_date, DEFAULT_PAYMENT_INTERVAL_TYPE,
                                  DEFAULT_PAYMENTS_INTERVAL, sale_total)
    sale.set_valid()
    return sale

#
# Main
#

def create_sales():
    conn = new_transaction()
    print_msg("Creating sales... ", break_line=False)

    sale_statuses = Sale.statuses.keys()
    sale_statuses.remove(Sale.STATUS_CANCELLED)
    clients = get_clients(conn)
    if not len(clients) >= DEFAULT_SALE_NUMBER:
        raise SellError("You don't have clients to create all the sales.")
    product_list = get_all_products(conn)
    if not len(product_list) >= DEFAULT_SALE_NUMBER:
        raise SellError("You don't have products to create all the sales.")
    salespersons = Person.getAdapterClass(ISalesPerson).select(connection=conn)
    if salespersons.count() < DEFAULT_SALE_NUMBER:
        raise ValueError('You should have at last %d salespersons defined '
                         'in database at this point, got %d instead' %
                         (DEFAULT_SALE_NUMBER, salespersons.count()))
    open_dates = [datetime.datetime.today(),
                  datetime.datetime.today() + datetime.timedelta(10),
                  datetime.datetime.today() + datetime.timedelta(15),
                  datetime.datetime.today() + datetime.timedelta(23)]
    installments_numbers = [i * 2 for i in range(1,
                                                 DEFAULT_SALE_NUMBER + 1)]
    for index, (open_date, status, salesperson, client, product,
                installments_number) in enumerate(zip(open_dates,
                                                      sale_statuses,
                                                      salespersons,
                                                      clients,
                                                      product_list,
                                                      installments_numbers)):
        _create_sale(conn, open_date, status, salesperson, client, index,
                     product, installments_number)
    set_current_user(
        Person.getAdapterClass(IUser).select(connection=conn)[0])
    cancelled_sale = _create_sale(conn, open_dates[0], Sale.STATUS_OPENED,
                                  salespersons[0], clients[0], index+1,
                                  product_list[0], installments_numbers[0])
    adapter = cancelled_sale.create_sale_return_adapter()
    adapter.confirm(cancelled_sale)
    conn.commit()
    print_msg("done.")

if __name__ == '__main__':
    create_sales()

