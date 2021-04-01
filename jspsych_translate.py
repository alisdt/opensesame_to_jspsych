#-*- coding:utf-8 -*-

"""
This file is part of OpenSesame.

OpenSesame is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

OpenSesame is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with OpenSesame.  If not, see <http://www.gnu.org/licenses/>.
"""

from pathlib import Path

from libopensesame.py3compat import *
from libqtopensesame.extensions import base_extension
from libqtopensesame.misc.translate import translation_context

from opensesame_to_jspsych import opensesame_to_jspsych

_ = translation_context(u'jspsych_translate', category=u'extension')

class jspsych_translate(base_extension):

    """
    desc:
        Translate the current experiment to jsPsych
    """

    def event_startup(self):

        self._widget = None
        self._jspsych_translate_action = self.qaction(
            u'applications-internet',
            u'JSPsychTranslate',
            self._do_translate,
        )
        self.add_action(
            self.get_submenu(u'tools'),
            self._jspsych_translate_action,
            3,
            False,
            False
        )

    def activate(self):
        pass

    def _do_translate(self):
        experiment = self.main_window.experiment
        start = self.main_window.experiment.var.start
        self.console.write(start+"\n")
        self.console.write(repr(experiment.items.items())+"\n")
        html, js = opensesame_to_jspsych(experiment)
        for text in [html, js, ""]:
            self.console.write("-----------------------\n")
            self.console.write(text+"\n")
        open("/home/alisdair/jspsych_translate/out/experiment.html","w").write(html)
        open("/home/alisdair/jspsych_translate/out/experiment.js","w").write(js)
