# -*- coding: utf-8 -*-
# Copyright 2017 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields
from odoo.tests import common
from datetime import timedelta


class TestProductExpiryAvailable(common.TransactionCase):

    def setUp(self):
        super(TestProductExpiryAvailable, self).setUp()

        self.product_1 = self.env.ref('stock.product_icecream')
        self.product_1.tracking = 'lot'
        self.warehouse_1 = self.env.ref('stock.warehouse0')

    def test_00_lot_product_available_today(self):
        lot_obj = self.env['stock.production.lot']
        removal_date = fields.Datetime.from_string(
            fields.Datetime.now()) + timedelta(days=5)
        # First create lot
        vals = {'removal_date': removal_date,
                'product_id': self.product_1.id
                }
        self.lot_1 = lot_obj.create(vals)
        # Create Inventory for product
        inventory = self.env['stock.inventory'].create({
            'name': 'Initial inventory',
            'filter': 'partial',
            'line_ids': [(0, 0, {
                'product_id': self.product_1.id,
                'prod_lot_id': self.lot_1.id,
                'product_uom_id': self.product_1.uom_id.id,
                'product_qty': 10,
                'location_id': self.warehouse_1.lot_stock_id.id
            })]
        })
        inventory.action_done()
        self.assertEqual(self.product_1.qty_available, 10)

        removal_date = fields.Datetime.from_string(
            fields.Datetime.now()) + timedelta(days=-5)
        vals = {'removal_date': removal_date,
                'product_id': self.product_1.id
                }
        self.lot_2 = lot_obj.create(vals)
        # Create Inventory for product
        inventory = self.env['stock.inventory'].create({
            'name': 'Initial inventory',
            'filter': 'partial',
            'line_ids': [(0, 0, {
                'product_id': self.product_1.id,
                'prod_lot_id': self.lot_2.id,
                'product_uom_id': self.product_1.uom_id.id,
                'product_qty': 20,
                'location_id': self.warehouse_1.lot_stock_id.id
            })]
        })
        inventory.action_done()
        self.assertEqual(self.product_1.qty_available, 10)

    def test_01_lot_product_available_tomorrow(self):
        lot_obj = self.env['stock.production.lot']
        removal_date = fields.Datetime.from_string(fields.Datetime.now())
        # First create lot
        vals = {'removal_date': removal_date,
                'product_id': self.product_1.id
                }
        self.lot_1 = lot_obj.create(vals)
        # Create Inventory for product
        inventory = self.env['stock.inventory'].create({
            'name': 'Initial inventory',
            'filter': 'partial',
            'line_ids': [(0, 0, {
                'product_id': self.product_1.id,
                'prod_lot_id': self.lot_1.id,
                'product_uom_id': self.product_1.uom_id.id,
                'product_qty': 10,
                'location_id': self.warehouse_1.lot_stock_id.id
            })]
        })
        inventory.action_done()
        # Unfortunately the lot expired today
        self.assertEqual(self.product_1.qty_available, 0)

    def test_02_lot_product_available_pivot(self):
        lot_obj = self.env['stock.production.lot']
        removal_date = fields.Datetime.from_string(fields.Datetime.now())
        # First create lot
        vals = {'removal_date': removal_date,
                'product_id': self.product_1.id
                }
        self.lot_1 = lot_obj.create(vals)
        # Create Inventory for product
        inventory = self.env['stock.inventory'].create({
            'name': 'Initial inventory',
            'filter': 'partial',
            'line_ids': [(0, 0, {
                'product_id': self.product_1.id,
                'prod_lot_id': self.lot_1.id,
                'product_uom_id': self.product_1.uom_id.id,
                'product_qty': 10,
                'location_id': self.warehouse_1.lot_stock_id.id
            })]
        })
        inventory.action_done()
        # Get pivot date on yesterday
        pivot_date = fields.Datetime.to_string(
            fields.Datetime.from_string(
                fields.Datetime.now()) + timedelta(days=-1))
        self.assertEqual(
            self.product_1.with_context(pivot_date=pivot_date).qty_available,
            10)
