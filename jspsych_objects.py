# Exist just to be translated to JS!

class TranslationContext(object):
    """
    Possibly unnecessary (would just a set do?) but leaves room for other
    bits of context to be added.
    This is an abundance of caution, unless people pick weird names in
    OpenSesame clashes *shouldn't* happen, but they are possible.
    """
    def __init__(self):
        self.names = set()

    def can_use_name(self, _name):
        return _name not in self.names

    def add_name(self, _name):
        self.names.add(_name)

class Timeline(object):
    def __init__(self, _timeline):
        self.timeline = _timeline

    def html_and_name(self):
        pass

class Loop(object):
    def __init__(self, inner_timeline):
        self._inner_timeline = inner_timeline

    def to_string(self):
        pass

class HTMLKeyboard(object):
    def __init__(self, item):
