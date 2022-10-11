#!/usr/bin/env python

from __future__ import absolute_import

import sys

import numpy as np

from .clustering import (
    affprop_clustering,
    agglomerative_clustering,
    kmeans_clustering,
    plot_dendrogram,
)
from .da import da_matrix
from .erel import erel_matrix
from .exceptions import InputError
from .helpers import processargs
from .molecule import Molecule
from .rmsd import rmsd_matrix

if __name__ == "__main__" or __name__ == "marc.marc":
    (
        basename,
        molecules,
        c,
        m,
        n_clusters,
        ewin,
        plotmode,
        verb,
    ) = processargs(sys.argv[1:])
else:
    exit(1)

# Fill in molecule data
l = len(molecules)
if verb > 0:
    print(
        f"marc has detected {l} molecules in input, and will select {n_clusters} most representative conformers using {c} clustering and {m} as metric."
    )
    if verb > 1 and ewin is not None:
        print(
            f"An energy window of {ewin} in energy units will be considered for the output conformers."
        )

# Generate the desired metric matrix
if m in ["rmsd", "ewrmsd", "mix"]:
    rmsd_matrix = rmsd_matrix(molecules)
    if plotmode > 1:
        plot_dendrogram(rmsd_matrix, "RMSD")
    A = rmsd_matrix

if m in ["erel", "ewrmsd", "ewda", "mix"]:
    energies = [molecule.energy for molecule in molecules]
    if None in energies:
        raise InputError(
            """One or more molecules do not have an associated energy. Cannot use
             energy metrics. Exiting."""
        )
    erel_matrix = erel_matrix(molecules)
    if plotmode > 1:
        plot_dendrogram(erel_matrix, "E_{rel}")
    A = erel_matrix

if m in ["da", "ewda", "mix"]:
    da_matrix = da_matrix(molecules)
    if plotmode > 1:
        plot_dendrogram(da_matrix, "Dihedral")
    A = da_matrix

# Mix the metric matrices if desired
if m == ["ewrmsd"]:
    rmsd_matrix = np.abs(rmsd_matrix) / np.max(rmsd_matrix)
    erel_matrix = np.abs(erel_matrix) / np.max(erel_matrix)
    A = rmsd_matrix * erel_matrix

if m == ["ewrda"]:
    da_matrix = np.abs(da_matrix) / np.max(da_matrix)
    erel_matrix = np.abs(erel_matrix) / np.max(erel_matrix)
    A = da_matrix * erel_matrix

if m == ["mix"]:
    rmsd_matrix = np.abs(rmsd_matrix) / np.max(rmsd_matrix)
    da_matrix = np.abs(da_matrix) / np.max(da_matrix)
    erel_matrix = np.abs(erel_matrix) / np.max(erel_matrix)
    A = da_matrix * erel_matrix * rmsd_matrix


# Time to cluster after scaling the matrix. Scaling choice is not innocent.

A = np.abs(A) / np.max(A)

if c == "kmeans":
    indices, clusters = kmeans_clustering(n_clusters, A, verb)

if c == "agglomerative":
    indices, clusters = agglomerative_clustering(n_clusters, A, verb)

if c == "affprop":
    indices, clusters = affprop_clustering(A, verb)

# If requested, prune again based on average cluster energies

if ewin is not None:
    energies = [molecule.energy for molecule in molecules]
    if None in energies:
        raise InputError(
            """One or more molecules do not have an associated energy. Cannot use
             energy metrics. Exiting."""
        )
    avgs = np.zeros(len(clusters), dtype=float)
    stds = np.zeros(len(clusters), dtype=float)
    for i, cluster in enumerate(clusters):
        energies = np.array(
            [molecule.energy for molecule in molecules[cluster]], dtype=float
        )
        avgs[i] = energy.mean
        stds[i] = energy.std * 0.5
    lowest = np.min(avgs)
    accepted = np.where(avgs < lowest + stds + ewin)
    for i, idx in enumerate(indices):
        if accepted[i]:
            if verb > 1:
                print(
                    f"Accepting selected conformer number {i} due to energy threshold."
                )
            pass
        if not accepted[i]:
            if verb > 1:
                print(f"Removed selected conformer number {i} due to energy threshold.")
            indices.pop(i)

# Write the indices that were selected

for i, idx in enumerate(indices):
    molecules[idx].write(f"{basename}_selected_{i}")
