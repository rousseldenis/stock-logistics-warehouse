# -*- coding: utf-8 -*-
# Copyright 2017 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class StockQuant(models.Model):

    _inherit = 'stock.quant'

    lot_id = fields.Many2one(
        'stock.production.lot',
        auto_join=True
    )
    reservation_id = fields.Many2one(
        'stock.move',
        auto_join=True
    )
