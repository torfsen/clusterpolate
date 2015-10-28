#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

# Copyright (c) 2015 Florian Brucker (mail@florianbrucker.de)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
Tests for the ``clusterpolate`` package.
"""

import math

from matplotlib.cm import summer
import matplotlib.pyplot as plt
import numpy as np
from nose.tools import eq_ as eq, ok_ as ok, raises

import clusterpolate as cp


# Prepare test data
points = [(0, 0), (1, 0), (1.5, 0)]
values = np.array([1, 2, 3])


def test_clusterpolate():
    targets = np.array([(0, 0), (1.0, 0), (1.5, 0)])
    pred, member = cp.clusterpolate(points, values, targets, radius=1)
    eq(pred.shape, (3,))
    eq(member.shape, (3,))
    ok(pred.min() >= values.min())
    ok(pred.max() <= values.max())
    ok(member.min() >= 0)
    ok(member.max() <= 1)


def test_image():
    size = (3, 2)
    targets, pred, member, img = cp.image(points, values, size,
                                          ((0, 0.5), (2, -0.5)),
                                          colormap=summer)
    eq(targets.shape, size + (2,))
    eq(pred.shape, size)
    eq(member.shape, size)

