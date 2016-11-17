# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011 Camptocamp SA (http://www.camptocamp.com)
#
# Copyright (C) 2004-Today Simplify Solutions. All Rights Reserved
# Author: Guewen Baconnier (Camptocamp)
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
from mako.template import Template
from mako.lookup import TemplateLookup

import os
import subprocess
import tempfile
import logging
from functools import partial


from mako import exceptions
from openerp.osv.orm import except_orm
from openerp.tools.translate import _
from openerp import pooler
from openerp import tools
from openerp.addons.report_webkit import webkit_report
from openerp.addons.report_webkit.report_helper import WebKitHelper
from openerp.modules.module import get_module_resource

_logger = logging.getLogger('picking.reports.webkit')


def mako_template(text):
    """Build a Mako template.

    This template uses UTF-8 encoding
    """
    tmp_lookup = TemplateLookup(
    )  # we need it in order to allow inclusion and inheritance
    return Template(text, input_encoding='utf-8', output_encoding='utf-8',
                    lookup=tmp_lookup)


class PickingAgregationWebKitParser(webkit_report.WebKitParser):

    def generate_pdf(self, comm_path, report_xml, header, footer, html_list,
                     webkit_header=False, parser_instance=False):
        """Call webkit in order to generate pdf"""
        if not webkit_header:
            webkit_header = report_xml.webkit_header
        fd, out_filename = tempfile.mkstemp(suffix=".pdf",
                                            prefix="webkit.tmp.")
        file_to_del = [out_filename]
        if comm_path:
            command = [comm_path]
        else:
            command = ['wkhtmltopdf']

        command.append('--quiet')
        # default to UTF-8 encoding.  Use <meta charset="latin-1"> to override.
        command.extend(['--encoding', 'utf-8'])
        # code for aged partner balance

        if header:
            with tempfile.NamedTemporaryFile(suffix=".head.html",
                                             delete=False) as head_file:
                head_file.write(self._sanitize_html(header))
            file_to_del.append(head_file.name)
            command.extend(['--header-html', head_file.name])
        if footer:
            with tempfile.NamedTemporaryFile(suffix=".foot.html",
                                             delete=False) as foot_file:
                foot_file.write(self._sanitize_html(footer))
            file_to_del.append(foot_file.name)
            command.extend(['--footer-html', foot_file.name])
        # code for aged partner balance

        if webkit_header.margin_top:
            command.extend(
                ['--margin-top',
                 str(webkit_header.margin_top).replace(',', '.')])
        if webkit_header.margin_bottom:
            command.extend(
                ['--margin-bottom',
                 str(webkit_header.margin_bottom).replace(',', '.')])
        if webkit_header.margin_left:
            command.extend(
                ['--margin-left',
                 str(webkit_header.margin_left).replace(',', '.')])
        if webkit_header.margin_right:
            command.extend(
                ['--margin-right',
                 str(webkit_header.margin_right).replace(',', '.')])
        if webkit_header.orientation:
            command.extend(
                ['--orientation',
                 str(webkit_header.orientation).replace(',', '.')])
        if webkit_header.format:
            command.extend(
                ['--page-size',
                 str(webkit_header.format).replace(',', '.')])

        if parser_instance.localcontext.get('additional_args', False):
            for arg in parser_instance.localcontext['additional_args']:
                command.extend(arg)

        count = 0
        for html in html_list:
            with tempfile.NamedTemporaryFile(suffix="%d.body.html" % count,
                                             delete=False) as html_file:
                count += 1
                html_file.write(self._sanitize_html(html))
            file_to_del.append(html_file.name)
            command.append(html_file.name)
        command.append(out_filename)
        stderr_fd, stderr_path = tempfile.mkstemp(text=True)
        file_to_del.append(stderr_path)
        try:
            status = subprocess.call(command, stderr=stderr_fd)
            os.close(stderr_fd)  # ensure flush before reading
            stderr_fd = None  # avoid closing again in finally block
            fobj = open(stderr_path, 'r')
            error_message = fobj.read()
            fobj.close()
            if not error_message:
                error_message = _('No diagnosis message was provided')
            else:
                error_message = _(
                    'The following diagnosis message was provided:\n') + \
                    error_message
            if status:
                raise except_orm(_('Webkit error'),
                                 _("The command 'wkhtmltopdf' failed with \
                                 error code = %s. Message: %s") %
                                 (status, error_message))
            with open(out_filename, 'rb') as pdf_file:
                pdf = pdf_file.read()
            os.close(fd)
        finally:
            if stderr_fd is not None:
                os.close(stderr_fd)
            for f_to_del in file_to_del:
                try:
                    os.unlink(f_to_del)
                except (OSError, IOError) as exc:
                    _logger.error('cannot remove file %s: %s', f_to_del, exc)
        return pdf
    # override needed to keep the attachments' storing procedure and
    # to print header and footer in the report

    def create_single_pdf(self, cursor, uid, ids, data, report_xml,
                          context=None):
        """generate the PDF"""
        print"report_xmlreport_xmlreport_xml", report_xml
        if context is None:
            context = {}
        htmls = []
        if report_xml.report_type != 'webkit':
            return super(HeaderFooterTextWebKitParser, self
                         ).create_single_pdf(cursor, uid, ids, data,
                                             report_xml, context=context)

        parser_instance = self.parser(cursor,
                                      uid,
                                      self.name2,
                                      context=context)

        self.pool = pooler.get_pool(cursor.dbname)
        objs = self.getObjects(cursor, uid, ids, context)
        parser_instance.set_context(objs, data, ids, report_xml.report_type)

        template = False

        if report_xml.report_file:
            path = get_module_resource(
                *report_xml.report_file.split(os.path.sep))
            if os.path.exists(path):
                template = file(path).read()
        if not template and report_xml.report_webkit_data:
            template = report_xml.report_webkit_data
        if not template:
            raise except_orm(
                _('Error!'), _('Webkit Report template not found !'))
        header = report_xml.webkit_header.html
        if not header and report_xml.header:
            raise except_orm(
                _('No header defined for this Webkit report!'),
                _('Please set a header in company settings.')
            )

        css = report_xml.webkit_header.css
        if not css:
            css = ''

        translate_call = partial(self.translate_call, parser_instance)
        # default_filters=['unicode', 'entity'] can be used to set global
        # filter
        body_mako_tpl = mako_template(template)
        helper = WebKitHelper(cursor, uid, report_xml.id, context)
        if report_xml.precise_mode:
            for obj in objs:
                parser_instance.localcontext['objects'] = [obj]
                try:
                    html = body_mako_tpl.render(helper=helper,
                                                css=css,
                                                _=translate_call,
                                                **parser_instance.localcontext)
                    htmls.append(html)
                except Exception:
                    msg = exceptions.text_error_template().render()
                    _logger.error(msg)
                    raise except_orm(_('Webkit render'), msg)
        else:
            try:
                html = body_mako_tpl.render(helper=helper,
                                            css=css,
                                            _=translate_call,
                                            **parser_instance.localcontext)
                htmls.append(html)
            except Exception:
                msg = exceptions.text_error_template().render()
                _logger.error(msg)
                raise except_orm(_('Webkit render'), msg)

        head = foot = False
        head_mako_tpl = mako_template(header)
        try:
            head = head_mako_tpl.render(helper=helper,
                                        css=css,
                                        _=translate_call,
                                        _debug=False,
                                        **parser_instance.localcontext)
        except Exception:
            raise except_orm(_('Webkit render!'),
                             exceptions.text_error_template().render())
        foot = False

        # code for aged partner balance
        footer = report_xml.webkit_header.footer_html
        if footer:
            foot_mako_tpl = mako_template(footer)
            try:
                foot = foot_mako_tpl.render(helper=helper,
                                            css=css,
                                            _=translate_call,
                                            **parser_instance.localcontext)
            except:
                msg = exceptions.text_error_template().render()
                _logger.error(msg)
                raise except_orm(_('Webkit render!'), msg)
        # code for aged partner balance

        if report_xml.webkit_debug:
            try:
                deb = body_mako_tpl.render(helper=helper,
                                           css=css,
                                           _debug=tools.ustr("\n".join(htmls)),
                                           _=translate_call,
                                           **parser_instance.localcontext)
            except Exception:
                msg = exceptions.text_error_template().render()
                _logger.error(msg)
                raise except_orm(_('Webkit render'), msg)
            return (deb, 'html')
        bin = self.get_lib(cursor, uid)
        pdf = self.generate_pdf(bin, report_xml, head, foot, htmls,
                                parser_instance=parser_instance)
        return (pdf, 'pdf')
