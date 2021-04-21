# Exist just to be translated to JS!

from pathlib import Path
import re

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
        # varname: nest count (in case same variable is reused in inner loop)
        # when nest count gets to 0 we delete it
        self._variables = {}

    def html_template(self):
        path = Path.resolve(Path.cwd() / Path(__file__))
        return open(path.parent / "experiment_template.html").read()

    def generate_html(self):
        # call after all JS has been generated to get plugins used
        plugin_html = ""
        for plugin in self.plugins_used:
            plugin_html += f'<script src="external/jspsych/plugins/jspsych-{plugin}.js"></script>\n'
        return self.html_template().replace('{plugins}', plugin_html)

    def register_variable(self, varname):
        if varname in self._variables:
            self._variables[varname] += 1
        else:
            self._variables[varname] = 1

    def unregister_variable(self, varname):
        if varname in self._variables:
            if self._variables[varname] == 0:
                raise Exception(f"Attempt to unregister {varname} which has 0 count")
            else:
                self._variables[varname] -= 1
                if self._variables[varname] == 0:
                    del self._variables[varname]
        else:
            raise Exception(f"Attempt to unregister {varname} which was not registered")

    def is_variable(self, varname):
        return varname in self._variables

    def sv(self, text, auto_func=True):
        """
        Substitute variables if present
        auto_func: Automatically create a function if needed to combine
         timeline vars and other values
        """
        text = text.strip()
        # firstly, is the text a single variable?
        m = re.match(r"^\[(\w+)\]$", text)
        if m is not None:
            varname = m.group(1).strip()
            if varname not in self._variables:
                raise Exception(f"Attempt to reference unregistered variable {varname}")
            return f'jsPsych.timelineVariable("{varname}")'
        # if not, write a function which substitutes the variable in
        # split text into chunks -- literal, variable, literal, variable
        matches = list(re.finditer(r"\[(\w+)\]", text))
        if not matches: # no variables -- return unmodified text
            # got to do some OpenSesame type guessing though
            if text.isnumeric():
                return text # TODO: account for reals
            else:
                return f'"{escape_for_output(text)}"'
        last_pos = 0
        inner_js_elements = []
        for match in matches:
            # string before match
            literal_raw = text[last_pos:match.span()[0]]
            if literal_raw: # exclude empty
                inner_js_elements.append(f'"{escape_for_output(literal_raw)}"')
            # variable string
            variable = text[match.span()[0]+1:match.span()[1]-1]
            inner_js_elements.append(f'jsPsych.timelineVariable("{variable}")')
            last_pos = match.span()[1]
        # last literal?
        literal_raw = text[last_pos:]
        if literal_raw:
            inner_js_elements.append(f'"{escape_for_output(literal_raw)}"')
        inner_js = "\n        +".join(el for el in inner_js_elements)
        if auto_func:
            return f"""\
function () {{
    return (
        {inner_js}
    );
}}
"""
        else:
            return inner_js

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
    def __init__(self, _context, _name, _html, _js, _condition):
        super().__init__(_context, _name)
        self.html = _html
        self.js = _js
        self.condition = _condition
        self.plugin = "call-function"

    def to_js(self):
        super().to_js()
        content = self.context.sv(self.html,auto_func=False)
        return f"""\
var {self.name} = {{
    type: "call-function",
    func: function () {{
        jspsych_globals["current_visual"] = (
            {content}
        );
        jspsych_globals["current_postload_js"] = function () {{
            {self.js}
        }};
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
        # register variable names before we go into the timeline
        for colname in self.table.column_names:
            self.context.register_variable(colname)
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
        for colname in self.table.column_names:
            self.context.unregister_variable(colname)
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
        self.plugin = "html-keyboard-response"

    def to_js(self):
        super().to_js()
        #print(self.name+" "+str(self.keys))
        keys_js = "jsPsych.ALL_KEYS"
        if isinstance(self.keys, list):
            keys_js = str(self.keys)
        duration_line = ""
        if self.duration is not None:
            duration_line = "duration: "+self.context.sv(self.duration)+","
        return f"""\
var {self.name} = {{
    type: "html-keyboard-response",
    stimulus: function () {{ return jspsych_globals["current_visual"]; }},
    {duration_line}
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
