class Tool:

    def __init__(self):
        pass

    @staticmethod
    def add_arguments(parser):
        pass

    @classmethod
    def from_keys(cls, args, args_keys, kwargs_keys):
        return cls(*[getattr(args, key) for key in args_keys], **{key: getattr(args, key) for key in kwargs_keys})

    def run(self):
        raise NotImplementedError