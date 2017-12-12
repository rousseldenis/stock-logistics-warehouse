# -*- coding: utf-8 -*-
# Copyright 2017 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProcurementCalendarAttendance(models.Model):

    _name = 'procurement.calendar.attendance'
    _inherits = {'resource.calendar.attendance': 'attendance_id'}
    _description = 'Procurement Calendar Attendance'

    attendance_id = fields.Many2one(
        'resource.calendar.attendance',
        string='Attendance',
        auto_join=True,
        required=True,
        ondelete='cascade',
    )
    procurement_calendar_id = fields.Many2one(
        'procurement.calendar',
        string='Calendar',
        required=True,
        readonly=True,
    )
    product_dependant = fields.Boolean(
        related='procurement_calendar_id.product_dependant',
        readonly=True
    )
    product_ids = fields.Many2many(
        'product.product',
        'calendar_attendance_product_product_rel',
        'attendance_id',
        'product_id',
        string='Products',
    )
    procurement_attendance_id = fields.Many2one(
        'resource.calendar.attendance',
        string="Scheduled Procurement",
        help="This is the expected delivery slot."
    )

    @api.model
    def create(self, vals):
        if 'procurement_calendar_id' in vals and 'calendar_id' not in vals:
            calendar = self.env['procurement.calendar'].browse(
                vals['procurement_calendar_id'])
            vals.update({'calendar_id': calendar.resource_id.id})
        return super(ProcurementCalendarAttendance, self).create(vals)

    @api.multi
    def unlink(self):
        self.mapped('attendance_id').unlink()
        res = super(ProcurementCalendarAttendance, self).unlink()
        return res
