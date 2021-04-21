# Takes a libopensesame.experiment.experiment
# Returns jsPsych as text

from pathlib import Path

from libqtopensesame.items.keyboard_response import keyboard_response
from libqtopensesame.items.loop import loop
from libqtopensesame.items.sequence import sequence
from libqtopensesame.items.sketchpad import sketchpad

from jspsych_objects import *
from sketchpad_to_html import SketchpadTranslator

def clean_type(t):
    return repr(type(t)).replace('<','').replace('>','')

class Convertor(object):
    def __init__(self, experiment):
        self.item_stack = []
        self.exp = experiment
        self.items = experiment.items
        self.start = experiment.var.start
        self.current_visual = None
        self.context = TranslationContext()

    def to_jspsych(self):
        # assert that start is a sequence
        assert type(self.items[self.start]) == sequence, "Start of experiment must be a sequence"
        top_sequence = self.sequence_to_jspsych(self.start, init=True)[0]
        # do JS first as plugins are collected on the way
        js = top_sequence.to_js()
        return self.context.generate_html(), js

    def sequence_to_jspsych(self, seq_item_name, condition="always", init=False):
        seq_item = self.items[seq_item_name]
        timeline_items = []
        for item, cond in seq_item.items:
            jsp_item = self.item_to_jspsych(item, condition=cond)
            if jsp_item is not None:
                if isinstance(jsp_item, list):
                    timeline_items += jsp_item
                else:
                    timeline_items.append(jsp_item)
        return [Timeline(self.context, seq_item_name, timeline_items, _init=init)]

    def item_to_jspsych(self, item_name, condition="always"):
        item = self.items[item_name]
        if type(item) == sequence:
            return self.sequence_to_jspsych(item_name, condition)
        elif type(item) == loop:
            return self.loop_to_jspsych(item_name, condition)
        elif type(item) == sketchpad:
            return self.sketchpad_to_jspsych(item_name, condition)
        elif type(item) == keyboard_response:
            return self.keyboard_to_jspsych(item_name, condition)
        elif 'notepad' in item.__class__.__name__:
            # horrible way to detect but not sure what else would work ....
            return self.notepad_to_jspsych(item_name, condition)
        else:
            return self.filler_to_jspsych(item_name, condition)

    def sketchpad_to_jspsych(self, spad_item_name, condition="always"):
        """
        We add a jsPsych code "trial" which just changes the current
        visual stimulus HTML and code to be run afterwards.
        This will be persistent across sounds / keyboard input
        until something changes it.
        Then look at "duration":
        - if "keypress", it's just a simple html-keyboard-response
        - if 0, no further action (the next items will determine what happens)
        - if a fixed duration, it's just a stimulus
          (a html-keyboard-response with no keys allowed)
        """
        result = []
        spad_item = self.items[spad_item_name]
        elements = spad_item.elements
        js, html = SketchpadTranslator(self.context, elements).to_js()
        result.append(ChangeVisualStim(
            self.context, spad_item_name+"_visual", html, js, condition
        ))
        duration_in = spad_item.var.duration.strip()
        try:
            duration = int(duration_in)
        except ValueError:
            # not an integer
            duration = duration_in
        if isinstance(duration, int):
            if duration != 0:
                # fixed duration, no keys -- just a stimulus
                result.append(HTMLKeyboard(
                    self.context, spad_item_name, keys=[], duration=int(duration)
                ))
                # if duration == 0, add nothing -- this is deliberate
        else:
            if duration == "keypress":
                result.append(HTMLKeyboard(
                    self.context, spad_item_name
                ))
            elif duration.startswith("[") and duration.endswith("]"):
                result.append(HTMLKeyboard(
                    self.context, spad_item_name, duration=duration
                ))
            else:
                # string but not "keypress" or variable -- this is an error
                raise Exception(f"Unknown value for duration in sketchpad: {duration}")

        return result

    def loop_to_jspsych(self, loop_item_name, condition="always"):
        loop_item = self.items[loop_item_name]
        dm = loop_item.dm
        inner_item_name = loop_item._item
        return [
            Loop(
                self.context,
                loop_item_name,
                self.item_to_jspsych(inner_item_name), # *
                dm
            )
        ]
        # * Needs to be a list -- but all *_to_jspsych functions return lists

    def keyboard_to_jspsych(self, kbd_item_name, condition="always"):
        kbd_item = self.items[kbd_item_name]
        allowed_responses = kbd_item.var.allowed_responses.split(";")
        return [HTMLKeyboard(self.context, kbd_item_name, keys=allowed_responses)]

    def notepad_to_jspsych(self, npd_item_name, condition="always"):
        npd_item = self.items[npd_item_name]
        return [Comment(self.context, npd_item_name, npd_item.var.get("note"))]

    def filler_to_jspsych(self, item_name, condition="always"):
        item = self.items[item_name]
        html = f"I am a filler item with type {clean_type(item)} and name {item_name}"
        return [
            ChangeVisualStim(
                self.context, item_name+"_visual", html, condition
            ),
            HTMLKeyboard(self.context, item_name)
        ]

def opensesame_to_jspsych(experiment):
    c = Convertor(experiment)
    html, js = c.to_jspsych()
    return (html, js)
