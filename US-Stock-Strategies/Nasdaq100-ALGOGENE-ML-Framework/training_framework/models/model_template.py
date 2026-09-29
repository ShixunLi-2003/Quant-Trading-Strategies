"""Copy this file and replace only Model internals."""


class Model:
    def __init__(self, **params):
        self.params = params

    def fit(self, x_train, y_train, x_validation, y_validation):
        raise NotImplementedError

    def predict(self, features):
        raise NotImplementedError

    def save(self, path):
        raise NotImplementedError
