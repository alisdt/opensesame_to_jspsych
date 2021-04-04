# Exist just to be translated to JS!

from pathlib import Path

def escape_for_output(html):
    return html.replace('"', r'\"')

def build_timeline(context, timeline):
    timeline_without_comments = [
        t for t in timeline
        if t.name not in context.comment_names
    ]
    code_str = "\n".join(
        t.to_js() for t in timeline_without_comments
    )
    timeline_str = ",".join(t.name for t in timeline_without_comments)
    return code_str, timeline_str

class TranslationContext:
    """
    Name tracking is an abundance of caution, unless people pick weird names in
    OpenSesame clashes *shouldn't* happen, but they are possible.
    Also holds setup at the start of the file, and the plugins used as we
    translate.
    """
    def __init__(self):
        self.names = set()
        self.comment_names = set() # to exclude from timelines
        self.setup = "var jspsych_globals = {};\n\n"
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


class JSPsychProducer:
    def __init__(self, _context, _name):
        self.context = _context
        self.name = self.get_unique_name(_name)
        self.context.names.add(self.name)
        self.plugin = None

    def get_unique_name(self, _name):
        attempt_name = _name
        count = 1
        while attempt_name in self.context.names:
            attempt_name = f"{_name}_{count}"
            count += 1
        return attempt_name

    def to_js(self):
        if self.plugin is not None:
            self.context.plugins_used.add(self.plugin)

class ChangeVisualStim(JSPsychProducer):
    def __init__(self, _context, _name, _html, _condition):
        super().__init__(_context, _name)
        self.html = _html
        self.condition = _condition
        self.plugin = "call-function"

    def to_js(self):
        super().to_js()
        return f"""\
var {self.name} = {{
    type: "call-function",
    func: function () {{
        jspsych_globals["current_visual"] = "{escape_for_output(self.html)}";
    }}
}};
"""

class Timeline(JSPsychProducer):
    def __init__(self, _context, _name, _timeline, _init=False):
        """
        When _init = True, call jsPsych.init (top timeline)
        """
        super().__init__(_context, _name)
        self.timeline = _timeline
        self.init = _init

    def to_js(self):
        super().to_js()
        result = ""
        if self.init:
            result += self.context.setup
        code_str, timeline_str = build_timeline(self.context, self.timeline)
        result += code_str
        if self.init:
            result += f"""\
jsPsych.init({{
    timeline: [{timeline_str}]
}});
"""
        else:
            result += f"""\
var {self.name} = {{
    timeline: [{timeline_str}]
}};
"""
        return result

class Loop(JSPsychProducer):
    def __init__(self, _context, _name, _inner_timeline, _table):
        super().__init__(_context, _name)
        self.inner_timeline = _inner_timeline
        self.table = _table

    def to_js(self):
        super().to_js()
        code_str, timeline_str = build_timeline(
            self.context, self.inner_timeline
        )
        timeline_variables_name = self.get_unique_name(
            f"{self.name}_timeline_variables"
        )
        table_contents = ',\n    '.join([
            "{"+", ".join(f"{colname}: {repr(cell)}" for colname, cell in row)+"}"
            for row in self.table
        ])
        return f"""\
{code_str}

var {timeline_variables_name} = [
    {table_contents}
];
var {self.name} = {{
    timeline: [{timeline_str}],
    timeline_variables: {timeline_variables_name}
}};
"""
        return result

class HTMLKeyboard(JSPsychProducer):
    """
    It looks odd that there's no visual stimulus here -- this is always set
    by a call-function "trial" from ChangeVisualStim
    """
    def __init__(
        self, _context, _name, keys=None, duration=None
    ):
        super().__init__(_context, _name)
        self.keys = keys
        self.duration = duration
        if self.duration is None:
            self.duration = '"keypress"'
        self.plugin = "html-keyboard-response"

    def to_js(self):
        super().to_js()
        #print(self.name+" "+str(self.keys))
        keys_js = "jsPsych.ALL_KEYS"
        if isinstance(self.keys, list):
            keys_js = str(self.keys)
        return f"""\
var {self.name} = {{
    type: "html-keyboard-response",
    stimulus: function () {{ return jspsych_globals["current_visual"]; }},
    duration: {self.duration},
    choices: {keys_js}
}};
"""

class Comment(JSPsychProducer):
    def __init__(self, _context, _name, _text):
        super().__init__(_context, _name)
        self.text = _text
        self.context.comment_names.add(_name)

    def to_js(self):
        super().to_js()
        return f"""\
/*
Auto-copied comment text from OpenSesame item {self.name}
{self.text}
*/
"""
