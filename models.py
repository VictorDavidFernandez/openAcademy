# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import models, fields, api, exceptions


class Course(models.Model):
    _name = 'openacademy.course'

    title = fields.Char(string='Title', required=True)
    description = fields.Char(string='Description')
    responsibleUser = fields.Many2one('res.users', string="Responsible user")
    session = fields.One2many('openacademy.session', 'course', string="Session")

    def copy(self, default=None):
        default = dict(default or {})

        copied_count = self.search_count(
            [('title', '=like', u"Copy of {}%".format(self.title))])
        if not copied_count:
            new_title = u"Copy of {}".format(self.title)
        else:
            new_title = u"Copy of {} ({})".format(self.title, copied_count)

        default['title'] = new_title
        return super(Course, self).copy(default)

    _sql_constraints = [
        ('title_check',
         'CHECK(title != description)',
         "The title and the description can't be the same"),

        ('title_unique',
         'UNIQUE(title)',
         "The course title must be unique"),
    ]


class Sessions(models.Model):
    _name = 'openacademy.session'
    name = fields.Char(string='Name', required=True)
    startDate = fields.Date(string='Start Date', default=fields.Date.today)
    duration = fields.Float(string='Duration')
    numberOfSeats = fields.Float(string='Number of seats')
    instructor = fields.Many2one('res.partner', string="Instructor",
                                 domain=[('instructor', '=', True),
                                         ('category_id.name', 'ilike', "Teacher")])
    course = fields.Many2one('openacademy.course', ondelete='cascade', string="Course")
    attendees = fields.Many2many('res.partner', 'openacademy_courses_sessions_rel', 'session_id', 'partnert_id',
                                 'Attendees')

    percentageOfSeats = fields.Float(string="Percentage of seats", compute='_percentage_of_seats')
    active = fields.Boolean(default=True)

    endDate = fields.Date(string="End Date", store=True, compute='_get_end_date', inverse='_set_end_date')

    attendeesNumber = fields.Integer(
        string="Attendees number", compute='_get_attendees_number', store=True)
    color = fields.Integer()

    @api.depends('attendees')
    def _get_attendees_number(self):
        for record in self:
            record.attendeesNumber = len(record.attendees)

    @api.depends('startDate', 'duration')
    def _get_end_date(self):
        for record in self:
            if not (record.startDate and record.duration):
                record.endDate = record.startDate
                continue

            start = fields.Datetime.from_string(record.startDate)
            duration = timedelta(days=record.duration, seconds=-1)
            record.endDate = start + duration

    def _set_end_date(self):
        for record in self:
            if not (record.startDate and record.endDate):
                continue

            startDate = fields.Datetime.from_string(record.startDate)
            endDate = fields.Datetime.from_string(record.endDate)
            record.duration = (endDate - startDate).days + 1

    @api.depends('numberOfSeats', 'attendees')
    def _percentage_of_seats(self):
        for record in self:
            if not record.numberOfSeats:
                record.percentageOfSeats = 0.0
            else:
                record.percentageOfSeats = 100.0 * len(record.attendees) / record.numberOfSeats

    @api.onchange('numberOfSeats', 'attendees')
    def _verify_valid_seats(self):
        if self.numberOfSeats < 0:
            return {
                'warning': {
                    'title': "Error",
                    'message': "The number of seats cannot go below 0.",
                },
            }
        if self.numberOfSeats < len(self.attendees):
            return {
                'warning': {
                    'title': "Error",
                    'message': "Too many attendees",
                },
            }

    @api.constrains('instructor', 'attendees')
    def _check_instructor(self):
        for record in self:
            if record.instructor in record.attendees:
                raise exceptions.ValidationError("The instructor of the session can't be an attendee")


class Partner(models.Model):
    _inherit = 'res.partner'

    instructor = fields.Boolean('Instructor', default=False)

    session_ids = fields.Many2many('openacademy.session', 'openacademy_courses_sessions_rel', 'partnert_id',
                                   'session_id', string="Attended Sessions")
