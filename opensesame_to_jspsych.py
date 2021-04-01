# Takes a libopensesame.experiment.experiment
# Returns jsPsych as text

from pathlib import Path

from libqtopensesame.items.loop import loop
from libqtopensesame.items.sequence import sequence
from libqtopensesame.items.sketchpad import sketchpad

# one-time setup at the start of the jsPsych script
SETUP = """
"""

def _nm(n):
    """
    Munge identifier names -- might need to avoid namespace clashes.
    For now, pass through for clarity.
    """
    return n

def clean_type(t):
    return repr(type(t)).replace('<','').replace('>','')

class Convertor(object):
    def __init__(self, experiment):
        self.item_stack = []
        self.exp = experiment
        self.items = experiment.items
        self.start = experiment.var.start
        self.plugins_used = set()

    def html_template(self):
        path = Path.resolve(Path.cwd() / Path(__file__))
        return open(path.parent / "experiment_template.html").read()

    def generate_html(self):
        # call after all JS has been generated to get plugins used
        plugin_html = ""
        for plugin in self.plugins_used:
            plugin_html += f'<script src="external/jspsych/plugins/jspsych-{plugin}.js"></script>\n'
        return self.html_template().replace('{plugins}', plugin_html)


    def to_jspsych(self):
        # assert that start is a sequence
        assert type(self.items[self.start]) == sequence, "Start of experiment must be a sequence"
        # Push items on to the item_stack so sequences are at the bottom (start)
        js = SETUP # generic node store, avoid using JS namespace
        js += self.sequence_to_jspsych(self.start)
        js += f"""
jsPsych.init({{
    timeline: [{_nm(self.start)}]
}});
"""
        return self.generate_html(), js

    def item_to_jspsych(self, item_name, condition="always"):
        item = self.items[item_name]
        if type(item) == sequence:
            return self.sequence_to_jspsych(item_name, condition)
        elif type(item) == loop:
            return self.loop_to_jspsych(item_name, condition)
        elif type(item) == sketchpad:
            return self.sketchpad_to_jspsych(item_name, condition)
        else:
            return self.filler_to_jspsych(item_name, condition)

    def sketchpad_to_jspsych(self, spad_item_name, condition="always"):
        elements = self.items[spad_item_name].elements
        spad_html = f"""\
{len(elements)} items:<br>{'<br>'.join(e.to_string() for e in elements)}
"""
        return f"""\
var {_nm(spad_item_name)} = {{
    type: "html-keyboard-response",
    stimulus: '{spad_html}'
}};
"""

    def sequence_to_jspsych(self, seq_item_name, condition="always"):
        timeline_name = _nm(seq_item_name+"_timeline")
        result = f'{timeline_name} = [];\n'
        for item, cond in self.items[seq_item_name].items:
            result += self.item_to_jspsych(item, condition=cond)
            result += f'{timeline_name}.push({_nm(item)});\n'
        result += f"""
var {_nm(seq_item_name)} = {{
    timeline: {timeline_name}
}};
"""
        return result

    def loop_to_jspsych(self, loop_item_name, condition="always"):
        """
        Uses a timeline variable on the table
        Todo: repeats, csv file, everything else
        """
        loop_item = self.items[loop_item_name]
        dm = loop_item.dm
        loop_inner_name = loop_item._item
        result = self.item_to_jspsych(loop_inner_name)
        timeline_variables_name = _nm(loop_item_name+"_timeline_variables")
        dm_contents = '\n'.join([
            "{"+", ".join(f"{colname}: {repr(cell)}" for colname, cell in row)+"}"
            for row in dm
        ])
        result += f"""
var {timeline_variables_name} = [
    {dm_contents}
]
var {_nm(loop_item_name)} = {{
    timeline: [{_nm(loop_inner_name)}],
    timeline_variables: {timeline_variables_name}
}}
"""
        return result


    def filler_to_jspsych(self, item_name, condition="always"):
        item = self.items[item_name]
        self.plugins_used.add("html-keyboard-response")
        return f"""
{_nm(item_name)} = {{
    type: "html-keyboard-response",
    stimulus: "I am a filler item with type {clean_type(item)} and name {item_name}"
}};
"""

def opensesame_to_jspsych(experiment):
    c = Convertor(experiment)
    html, js = c.to_jspsych()
    return (html, js)
