import numpy as np
import pandas as pd
from .stats import WOE
from sklearn.base import TransformerMixin

from .utils import to_ndarray, np_count, bin_by_splits
from .merge import DTMerge, ChiMerge, StepMerge, QuantileMerge, KMeansMerge



class WOETransformer(TransformerMixin):

    def fit(self, X, y, **kwargs):
        if not isinstance(X, pd.DataFrame):
            self.values_, self.woe_ = self._fit_woe(X, y, **kwargs)
            return self

        if isinstance(y, str):
            y = X.pop(y)

        self.values_ = dict()
        self.woe_ = dict()
        for col in X:
            self.values_[col], self.woe_[col] = self._fit_woe(X[col], y)

        return self

    def _fit_woe(self, X, y):
        t_counts_0 = np_count(y, 0, default = 1)
        t_counts_1 = np_count(y, 1, default = 1)

        values = np.unique(X)
        l = len(values)
        woe = np.zeros(l)

        for i in range(l):
            sub_target = y[X == values[i]]

            sub_0 = np_count(sub_target, 0, default = 1)
            sub_1 = np_count(sub_target, 1, default = 1)

            y_prob = sub_1 / t_counts_1
            n_prob = sub_0 / t_counts_0

            woe[i] = WOE(y_prob, n_prob)

        return values, woe


    def transform(self, X, ix = 0):
        if not isinstance(self.values_, dict):
            return self._transform_apply(X, self.values_, self.woe_)

        res = X.copy()
        for col in X:
            if col in self.values_:
                res[col] = self._transform_apply(X[col], self.values_[col], self.woe_[col])

        return res


    def _transform_apply(self, X, value, woe):
        X = to_ndarray(X)
        res = np.zeros(len(X))

        for i in range(len(value)):
            res[X == value[i]] = woe[i]

        return res


class Combiner(TransformerMixin):
    def fit(self, X, y = None, **kwargs):
        if not isinstance(X, pd.DataFrame):
            self.splits_, self.transer_ = self._merge(X, y = y, **kwargs)
            return self

        if isinstance(y, str):
            y = X.pop(y)

        self.splits_ = dict()
        self.transer_ = dict()
        for col in X:
            self.splits_[col], self.transer_[col] = self._merge(X[col], y = y, **kwargs)

        return self

    def _merge(self, X, y = None, method = 'chi', **kwargs):
        X = to_ndarray(X)

        if y is not None:
            y = to_ndarray(y)

        transer = False
        if not np.issubdtype(X.dtype, np.number):
            transer = WOETransformer()
            source = X.copy()
            X = transer.fit_transform(X, y)

        if method is 'dt':
            splits = DTMerge(X, y, **kwargs)
        elif method is 'chi':
            splits = ChiMerge(X, y, **kwargs)
        elif method is 'quantile':
            splits = QuantileMerge(X, **kwargs)
        elif method is 'step':
            splits = StepMerge(X, **kwargs)
        elif method is 'kmeans':
            splits = KMeaMerge(X, target = y, **kwargs)

        return splits, transer

    def transform(self, X):
        if not isinstance(self.splits_, dict):
            return self._transform_apply(X, self.splits_, self.transer_)

        res = X.copy()
        for col in X:
            if col in self.splits_:
                res[col] = self._transform_apply(X[col], self.splits_[col], self.transer_[col])

        return res

    def _transform_apply(self, X, splits, transer = False):
        X = to_ndarray(X)
        if transer:
            X = transer.transform(X)

        if len(splits):
            bins = bin_by_splits(X, splits)
        else:
            bins = np.zeros(len(X))

        return bins
