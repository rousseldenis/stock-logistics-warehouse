# -*- coding: utf-8 -*-
# Copyright 2017 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class ProcurementCalendar(models.Model):

    _name = 'procurement.calendar'
    _inherits = {'resource.calendar': 'resource_id'}
    _description = 'Procurement Calendar'

    active = fields.Boolean(
        default=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string="Partner"
    )
    resource_id = fields.Many2one(
        'resource.calendar',
        required=True,
        auto_join=True,
        ondelete='cascade',
    )
    attendance_ids = fields.One2many(
        'procurement.calendar.attendance',
        'procurement_calendar_id',
        string="Attendances"
    )
    product_dependant = fields.Boolean()
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        index=True
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        index=True
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.user.company_id
    )

    _sql_constraints = [
        ('location_uniq',
         'unique (active, location_id)',
         'You cannot have several active calendars for one location.'),
    ]
    _sql_constraints = [
        ('warehouse_uniq',
         'unique (active, warehouse_id)',
         'You cannot have several active calendars for one warehouse.'),
    ]

    @api.multi
    def get_attendances_for_weekday(self, day_dt):
        self.ensure_one()
        attendances = self.resource_id.get_attendances_for_weekday(day_dt)
        p_attendances = self.mapped('attendance_ids').filtered(
            lambda a: a.attendance_id in attendances)
        return p_attendances

    @api.multi
    def _schedule_days(self, days, new_date, compute_leaves=False):
        self.ensure_one()
        return self.resource_id._schedule_days(
            days, new_date, compute_leaves=compute_leaves)

    @api.multi
    def _get_next_date(self, date_t):
        new_date = date_t
        res = self._schedule_days(1, new_date, compute_leaves=True)
        number = 0
        while res and number < 100:
            number += 1
            new_date = res[0][1] + relativedelta(days=1)
            res = self._schedule_days(1, new_date, compute_leaves=True)
        # number as safety pall for endless loops
        if number >= 100:
            res = False
        if res:
            return (new_date, res[0][1])

    @api.multi
    def unlink(self):
        self.mapped('resource_id').unlink()
        res = super(ProcurementCalendar, self).unlink()
        return res
