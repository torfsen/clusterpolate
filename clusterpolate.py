#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

# Copyright (c) 2015 Florian Brucker (mail@florianbrucker.de).
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
Clusterpolate -- Inter- and extrapolation for clustered data.

Traditional approaches for inter- and extrapolation of scattered data
work on a filled rectangular area surrounding the data points or in
their filled convex hull. However, scattered data often consists of
different clusters of irregular shapes and usually contains areas where
there is simply no data. Forcing such data into a traditional inter-
or extrapolation scheme often does not lead to the desired results.

Heatmaps, on the other hand, deal well with scattered data but often do
not provide real interpolation: Instead they usually use raw sums of
kernel functions which overestimate the target value in densely
populated areas.

Clusterpolation is a hybrid inter- and extrapolation scheme to fix this.
It uses kernel functions for a weighted inter- and extrapolation of
local values, as well as for a density estimation of the data. The
latter is used to assign a membership degree to clusterpolated points:
Points with a low membership degree lie in an area where there's just
not enough data.

Raw clusterpolation is available via :py:func:`clusterpolate` and images
of clusterpolated data can be generated via :py:func:`image`.
"""

from __future__ import division

import numpy as np
import PIL.Image
import sklearn.neighbors


__all__ = ['bounding_box', 'bump', 'clusterpolate', 'image']


def bump(r):
    """
    Factory for bump kernel functions.

    ``r`` is the radius of the bump function.

    The returned bump function assumes that all values in the input
    vector are non-negative.
    """
    ir2 = (1.0 / r) ** 2
    n = np.exp(1)

    def kernel(dist):
        result = np.zeros(dist.shape)
        close = dist < r
        result[close] = n * np.exp(-1 / (1 - ir2 * dist[close]**2))
        return result

    return kernel


def clusterpolate(points, values, targets, radius=1, kernel_factory=bump,
                  neighbors=None):
    """
    Clusterpolate data.

    ``points`` (array-like) are the data points and ``values``
    (array-like) are the associated values. ``targets`` (array-like) are
    the points at which the data should be clusterpolated.

    ``radius`` (float) is the radius of each data point's kernel.

    ``kernel_factory`` is a function that takes a radius and returns
    a corresponding kernel function. The kernel function must accept
    an array of distances (>= 0) and return the corresponding kernel
    values. The kernel function must be normalized (a distance of 0
    must yield a value of 1) and it should be zero for distances greater
    than ``radius``.

    Neighbor lookup is done using an instance of
    :py:class:`sklearn.neighbors.NearestNeighbors`, constructed with
    the default options. You can pass an instance that is configured
    to suit your data via the ``neighbors`` parameter.

    Returns two arrays. The first contains the predicted value for the
    corresponding target point, and the second contains the target
    point's degree of membership (a float between 0 and 1).
    """

    # Accept lists as inputs
    points = np.array(points)
    values = np.array(values)
    if points.shape[0] != values.shape[0]:
        raise ValueError('The numbers of points and values must match.')
    targets = np.array(targets)

    if neighbors is None:
        neighbors = sklearn.neighbors.NearestNeighbors(radius=radius)
    kernel = kernel_factory(radius)

    neighbors.fit(points)
    dists, inds = neighbors.radius_neighbors(targets)

    predictions = np.zeros(targets.shape[0])
    membership = np.zeros(targets.shape[0])
    for i, (dist, ind) in enumerate(zip(dists, inds)):
        weights = kernel(dist)
        weights_sum = np.sum(weights)
        if weights_sum > 0:
            predictions[i] = np.sum(weights * values[ind]) / weights_sum
            membership[i] = weights.max()

    return predictions, membership


def image(points, values, size, area=None, normalize=True, colormap=None,
          **kwargs):
    """
    Create an image for clusterpolated data.

    ``points`` and ``values`` is the input data, see
    :py:func:`clusterpolate`.

    ``size`` is a 2-tuple containing the image dimensions.

    ``area`` is an optional  2-tuple of 2-tuples, specifying the
    top-left and bottom-right corner of the sampling area. If it is not
    given then the points' bounding box is used.

    If ``normalize`` is true then the clusterpolated values are
    normalized to the range ``[0, 1]``. If you set this to ``False`` you
    should ensure that input values are already in that range.

    ``colormap`` is an optional callback that can be used to color the
    clusterpolated values. It should accept values in a 2D array and
    return the corresponding colors in an array of the same shape but
    with an extra dimension containing the RGB components (between 0 and
    1). The olormaps shipped with :py:pkg:`matplotlib` are a good
    choice. If no colormap is given then a grayscale image is generated.

    Any additional keyword-argument is passed on to
    :py:func:`clusterpolate`.

    This function returns 4 values: The first 3 are arrays containing
    the pixel coordinates, the clusterpolated values, and the membership
    degrees. The last one is the generated image as an instance of
    :py:class:`PIL.Image.Image`.
    """
    if area is None:
        if len(points) < 2:
            raise ValueError('Need at least 2 points for automatic area ' +
                             'calculation.')
        area = bounding_box(points)
    x = np.linspace(area[0][0], area[1][0], size[0])
    y = np.linspace(area[0][1], area[1][1], size[1])
    targets = np.vstack(np.meshgrid(x, y)).reshape(2, -1).T

    predictions, memberships = clusterpolate(points, values, targets, **kwargs)
    predictions = predictions.reshape(size)
    memberships = memberships.reshape(size)

    if normalize:
        pmin = predictions.min()
        pmax = predictions.max()
        predictions = (predictions - pmin) / (pmax - pmin)
    if colormap is None:
        bands = (PIL.Image.fromarray(np.uint8(255 * predictions)),)
        mode = 'LA'
    else:
        rgba = PIL.Image.fromarray(np.uint8(255 * colormap(predictions)))
        bands = rgba.split()[:3]
        mode = 'RGBA'
    alpha = PIL.Image.fromarray(np.uint8(255 * memberships.reshape(size)))
    bands += (alpha,)
    img = PIL.Image.merge(mode, bands)
    return targets, predictions, memberships, img


def bounding_box(points):
    """
    Compute a point cloud's bounding box.

    ``points`` is a list or array of 2D points.

    The return value is a 2x2 tuple containing the upper left and the
    lower right bounding box corners.
    """
    p = np.array(points)
    return ((p[:, 0].min(), p[:, 1].min()), (p[:, 0].max(), p[:, 1].max()))


if __name__ == '__main__':

    import math
    from matplotlib.cm import summer

    n = 500
    angles = np.random.normal(0, 0.75, n) - 0.1 * math.pi
    radii = np.random.normal(1, 0.05, n)
    points = np.vstack((radii * np.sin(angles), radii * np.cos(angles))).T
    values = np.sin(angles) + np.random.normal(0, 0.5, n)
    size = (400, 400)
    area = ((-1.5, -1.5), (1.5, 1.5))

    _, _, _, img = image(points, values, size, area, radius=0.2,
                         colormap=summer)
    img.save('clusterpolate.png')

