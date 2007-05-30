# -*- Mode: Python; coding: iso-8859-1 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2007 Async Open Source <http://www.async.com.br>
## All rights reserved
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., or visit: http://www.gnu.org/.
##
## Author(s):   Johan Dahlin <jdahlin@async.com.br>
##              Fabio Morbec <fabio@async.com.br>
##

from sqlobject.viewable import Viewable
from sqlobject.sqlbuilder import func, AND, INNERJOINOn, LEFTJOINOn

from stoqlib.domain.product import (Product, ProductAdaptToSellable,
                                    ProductAdaptToStorable,
                                    ProductStockItem,
                                    ProductHistory)
from stoqlib.domain.sellable import ASellable, SellableUnit, BaseSellableInfo
from stoqlib.domain.stock import AbstractStockItem

class ProductFullStockView(Viewable):
    """
    Stores information about products.
    This view is used to query stock information on a certain branch.

    @cvar id: the id of the asellable table
    @cvar barcode: the sellable barcode
    @cvar status: the sellable status
    @cvar cost: the sellable cost
    @cvar price: the sellable price
    @cvar is_valid_model: the sellable is_valid_model system attribute
    @cvar description: the sellable description
    @cvar unit: the unit of the product
    @cvar product_id: the id of the product table
    @cvar branch_id: the id of person_adapt_to_branch table
    @cvar stock: the stock of the product
     """

    columns = dict(
        id=ASellable.q.id,
        barcode=ASellable.q.barcode,
        status=ASellable.q.status,
        cost=ASellable.q.cost,
        price=BaseSellableInfo.q.price,
        is_valid_model=BaseSellableInfo.q._is_valid_model,
        description=BaseSellableInfo.q.description,
        unit=SellableUnit.q.description,
        product_id=Product.q.id,
        stock=func.SUM(AbstractStockItem.q.quantity +
                       AbstractStockItem.q.logic_quantity),
        )

    joins = [
        # Sellable unit
        LEFTJOINOn(None, SellableUnit,
                   SellableUnit.q.id == ASellable.q.unitID),
        # Product
        INNERJOINOn(None, ProductAdaptToSellable,
                    ProductAdaptToSellable.q.id == ASellable.q.id),
        INNERJOINOn(None, Product,
                    Product.q.id == ProductAdaptToSellable.q._originalID),
        # Product Stock Item
        LEFTJOINOn(None, ProductAdaptToStorable,
                   ProductAdaptToStorable.q._originalID == Product.q.id),
        LEFTJOINOn(None, ProductStockItem,
                   ProductStockItem.q.storableID ==
                   ProductAdaptToStorable.q.id),
        LEFTJOINOn(None, AbstractStockItem,
                   AbstractStockItem.q.id == ProductStockItem.q.id),
        ]

    clause = AND(
        BaseSellableInfo.q.id == ASellable.q.base_sellable_infoID,
        BaseSellableInfo.q._is_valid_model == True,
        )

    @classmethod
    def select_by_branch(cls, query, branch, connection=None):
        if branch:
            branch_query = AbstractStockItem.q.branchID == branch.id
            if query:
                query = AND(query, branch_query)
            else:
                query = branch_query

        return cls.select(query, connection=connection)

    @property
    def product(self):
        return Product.get(self.product_id, connection=self.get_connection())


class ProductQuantityView(Viewable):
    """
    Stores information about products solded and received.

    @cvar id: the id of the sellable_id of products_quantity table
    @cvar description: the product description
    @cvar branch_id: the id of person_adapt_to_branch table
    @cvar quantity_sold: the quantity solded of product
    @cvar quantity_received: the quantity received of product
    @cvar branch: the id of the branch_id of producst_quantity table
    @cvar date_sale: the date of product's sale
    @cvar date_received: the date of product's received
     """

    columns = dict(
        id=ProductHistory.q.sellableID,
        description=BaseSellableInfo.q.description,
        branch=ProductHistory.q.branchID,
        sold_date=ProductHistory.q.sold_date,
        received_date=ProductHistory.q.received_date,
        quantity_sold=func.SUM(ProductHistory.q.quantity_sold),
        quantity_received=func.SUM(ProductHistory.q.quantity_received),
        )

    hidden_columns = ['sold_date', 'received_date']

    joins = [
        INNERJOINOn(None, ASellable,
                    ProductHistory.q.sellableID == ASellable.q.id),
        INNERJOINOn(None, BaseSellableInfo,
                    ASellable.q.base_sellable_infoID == BaseSellableInfo.q.id)
    ]
