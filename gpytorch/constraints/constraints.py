#!/usr/bin/env python3

import math
import torch
from torch.nn.functional import softplus, sigmoid
from ..utils.transforms import _get_inv_param_transform, inv_sigmoid, inv_softplus
from torch.nn import Module


class Interval(Module):
    def __init__(
        self,
        lower_bound,
        upper_bound,
        transform=sigmoid,
        inv_transform=inv_sigmoid,
    ):
        """
        Defines an interval constraint for GP model parameters, specified by a lower bound and upper bound. For usage
        details, see the documentation for :meth:`~gpytorch.module.Module.register_constraint`.

        Args:
            - lower_bound (float or torch.Tensor):
        """
        if not torch.is_tensor(lower_bound):
            lower_bound = torch.tensor(lower_bound)

        if not torch.is_tensor(upper_bound):
            upper_bound = torch.tensor(upper_bound)

        if torch.any(upper_bound < math.inf) and torch.any(lower_bound > -math.inf) and transform != sigmoid:
            raise RuntimeError("Cannot enforce a double sided bound with a non-sigmoid transform!")

        super().__init__()

        self.lower_bound = lower_bound
        self.upper_bound = upper_bound

        self._transform = transform

        if transform is not None and inv_transform is None:
            self._inv_transform = _get_inv_param_transform(transform)

    def _apply(self, fn):
        self.lower_bound = fn(self.lower_bound)
        self.upper_bound = fn(self.upper_bound)
        return super()._apply(fn)

    @property
    def enforced(self):
        return self._transform is not None

    def check(self, tensor):
        return torch.all(tensor <= self.upper_bound) and torch.all(tensor >= self.lower_bound)

    def intersect(self, other):
        """
        Returns a new Interval constraint that is the intersection of this one and another specified one.

        Args:
            other (Interval): Interval constraint to intersect with

        Returns:
            Interval: intersection if this interval with the other one.
        """
        if self.transform != other.transform:
            raise RuntimeError("Cant intersect Interval constraints with conflicting transforms!")

        lower_bound = torch.max(self.lower_bound, other.lower_bound)
        upper_bound = torch.min(self.upper_bound, other.upper_bound)
        return Interval(lower_bound, upper_bound)

    def transform(self, tensor):
        """
        Transforms a tensor to satisfy the specified bounds.

        If upper_bound is finite, we assume that `self.transform` saturates at 1 as tensor -> infinity. Similarly,
        if lower_bound is finite, we assume that `self.transform` saturates at 0 as tensor -> -infinity.

        Example transforms for one of the bounds being finite include torch.exp and torch.nn.functional.softplus.
        An example transform for the case where both are finite is torch.nn.functional.sigmoid.
        """
        if not self.enforced:
            return tensor

        transformed_tensor = self._transform(tensor)

        upper_bound = self.upper_bound.clone()
        upper_bound[upper_bound == math.inf] = 1.
        lower_bound = self.lower_bound.clone()
        lower_bound[lower_bound == -math.inf] = 0.

        transformed_tensor = transformed_tensor * upper_bound
        transformed_tensor = transformed_tensor + lower_bound

        return transformed_tensor

    def inverse_transform(self, transformed_tensor):
        """
        Applies the inverse transformation.
        """
        if not self.enforced:
            return transformed_tensor

        upper_bound = self.upper_bound
        upper_bound[upper_bound == math.inf] = 1
        lower_bound = self.lower_bound
        lower_bound[lower_bound == -math.inf] = 0

        tensor = transformed_tensor - self.lower_bound
        tensor = tensor / self.upper_bound

        tensor = self._inv_transform(tensor)

        return tensor

    def __repr__(self):
        if self.lower_bound.numel() == 1 and self.upper_bound.numel() == 1:
            return self._get_name() + f'({self.lower_bound}, {self.upper_bound})'
        else:
            return super().__repr__()

    def __iter__(self):
        yield self.lower_bound
        yield self.upper_bound


class GreaterThan(Interval):
    def __init__(
        self,
        lower_bound,
        transform=softplus,
        inv_transform=inv_softplus,
        active=True,
    ):
        super().__init__(
            lower_bound=lower_bound,
            upper_bound=math.inf,
            transform=transform,
            inv_transform=inv_transform
        )

    def __repr__(self):
        if self.lower_bound.numel() == 1:
            return self._get_name() + f'({self.lower_bound})'
        else:
            return super().__repr__()


class Positive(GreaterThan):
    def __init__(self, transform=softplus, inv_transform=inv_softplus):
        super().__init__(
            lower_bound=0.,
            transform=transform,
            inv_transform=inv_transform
        )

    def __repr__(self):
        return self._get_name() + '()'


class LessThan(Interval):
    def __init__(self, upper_bound, transform=softplus, inv_transform=inv_softplus):
        super().__init__(
            lower_bound=-math.inf,
            upper_bound=upper_bound,
            transform=transform,
            inv_transform=inv_transform
        )

    def transform(self, tensor):
        if not self.enforced:
            return tensor

        transformed_tensor = -self.transform(-tensor)
        transformed_tensor = transformed_tensor + self.upper_bound
        return transformed_tensor

    def inverse_transform(self, transformed_tensor):
        if not self.enforced:
            return transformed_tensor

        tensor = transformed_tensor - self.upper_bound
        tensor = -self._inv_transform(-tensor)
        return tensor

    def __repr__(self):
        return self._get_name() + f'({self.upper_bound})'
