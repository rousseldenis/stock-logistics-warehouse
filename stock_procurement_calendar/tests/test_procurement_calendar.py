# -*- coding: utf-8 -*-
# Copyright 2017 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime
from mock import patch, Mock
from odoo import fields
from odoo.tests import common


class TestProcurementCalendar(common.TransactionCase):

    def setUp(self):
        res = super(TestProcurementCalendar, self).setUp()

        self.product_11 = self.env.ref('product.product_product_11')

        vals = {
            'name': 'SEQUENCE PICK'
        }
        self.sequence1 = self.env['ir.sequence'].create(vals)

        vals = {
            'name': 'PICKING',
            'sequence_id': self.sequence1.id,
            'code': 'internal'
        }
        self.picking_type1 = self.env['stock.picking.type'].create(vals)

        self.route_1 = self.env['stock.location.route'].create({
            'name': 'Stock to Output'
        })

        vals = {
            'name': 'Stock => Output',
            'action': 'move',
            'location_id': self.ref('stock.stock_location_output'),
            'location_src_id': self.ref('stock.stock_location_stock'),
            'procure_method': 'make_to_stock',
            'route_id': self.route_1.id,
            'picking_type_id': self.picking_type1.id
        }
        self.env['procurement.rule'].create(vals)

        self.product_11.route_ids += self.route_1

        return res

    @patch.object(fields.Datetime, 'now', return_value='2017-11-20 08:00:00')
    @patch('datetime.datetime')
    def test_00_run_procurement(self, mock_now, fields_now):
        mock_now.now = Mock(return_value=datetime(2017, 11, 20, 8, 0, 0))
        self.env['procurement.order']._fields['date_planned'].default =\
            fields.Datetime.now
        monday = self.env.ref(
            'stock_procurement_calendar.'
            'procurement_calendar_output_attendance_m'
        )
        stock_monday = self.env.ref(
            'stock_procurement_calendar.procurement_calendar_1_attendance_mm')
        # Monday
        # Product 11 - Supplier info 8 - delay 2
        vals = {
            'name': 'Procurement Test 1',
            'location_id': self.ref('stock.stock_location_output'),
            'product_id': self.ref('product.product_product_11'),
            'product_qty': 10.0,
            'product_uom': self.ref('product.product_uom_unit')
        }
        self.procurement = self.env['procurement.order'].with_context(
            procurement_autorun_defer=True).create(vals)
        self.procurement.run()
        self.assertEquals(
            self.env.ref(
                'stock_procurement_calendar.procurement_calendar_output'),
            self.procurement.procurement_location_calendar_id
        )
        self.assertEquals(
            self.env.ref(
                'stock_procurement_calendar.procurement_calendar_1'
            ),
            self.procurement.procurement_calendar_id
        )
        self.assertEquals(
            monday,
            self.procurement.procurement_location_attendance_id
        )
        self.assertEquals(
            stock_monday,
            self.procurement.procurement_attendance_id
        )
