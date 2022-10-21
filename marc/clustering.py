#!/usr/bin/env python

import matplotlib
import numpy as np

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import scipy.cluster.hierarchy
import scipy.cluster.vq
from scipy.spatial.distance import euclidean, squareform
from sklearn.cluster import DBSCAN, AffinityPropagation, AgglomerativeClustering, KMeans
from sklearn.manifold import MDS
from sklearn.neighbors import NearestCentroid


def plot_dendrogram(m: np.ndarray, label: str, verb=0):
    if verb > 0:
        print(f"Max pairwise {label}: {np.max(m)} in {label} units.")
        if verb > 2:
            print(f"Distance matrix is:\n {m}")
    assert np.all(m - m.T < 1e-6)
    reduced_distances = squareform(m, force="tovector")
    linkage = scipy.cluster.hierarchy.linkage(reduced_distances, method="single")
    plt.title(f"{label} average linkage hierarchical clustering")
    dn = scipy.cluster.hierarchy.dendrogram(
        linkage, no_labels=True, count_sort="descendent"
    )
    if verb > 0:
        print(f"Saving dendrogram plot as {label}_dendrogram.png in working directory.")
    plt.savefig(f"{label}_dendrogram.png")
    plt.close()


def kmeans_clustering(n_clusters, m: np.ndarray, rank=2, verb=0):
    mds = MDS(dissimilarity="precomputed", n_components=rank, n_init=50)
    x = mds.fit_transform(m)
    if n_clusters is None:
        nm = m.shape[0]
        percentages = list(
            set(
                [
                    min(max(int(nm * percentage), 2), 50)
                    for percentage in [0.01, 0.05, 0.1, 0.25, 0.5]
                ]
            )
        )
        gaps = gap(x, nrefs=max(nm, 50), ks=percentages)
        n_clusters = max(percentages[np.argmax(gaps)], 2)
    km = KMeans(n_clusters=n_clusters, n_init=50)
    cm = km.fit_predict(x)
    u, c = np.unique(cm, return_counts=True)
    closest_pt_idx = []
    clusters = []
    if verb > 1:
        print(
            f"{u[-1]+1} unique clusters found: {u} \nWith counts: {c} \nAdding up to {np.sum(c)}"
        )
    for iclust in range(u.size):

        # get all points assigned to each cluster:
        clusters.append(np.where(km.labels_ == iclust)[0])

        # get all indices of points assigned to this cluster:
        cluster_pts_indices = np.where(km.labels_ == iclust)[0]

        cluster_cen = km.cluster_centers_[iclust]
        min_idx = np.argmin(
            [euclidean(x[idx], cluster_cen) for idx in cluster_pts_indices]
        )

        # Testing:
        if verb > 1:
            print(
                f"Closest index of point to cluster {iclust} center has index {cluster_pts_indices[min_idx]}"
            )
        closest_pt_idx.append(cluster_pts_indices[min_idx])
    return closest_pt_idx, clusters


def affprop_clustering(m, verb=0):
    m = np.ones_like(m) - m
    ap = AffinityPropagation(affinity="precomputed")
    cm = ap.fit_predict(m)
    u, c = np.unique(cm, return_counts=True)
    closest_pt_idx = []
    clusters = []
    if verb > 1:
        print(
            f"{u[-1]+1} unique clusters found: {u} \nWith counts: {c} \nAdding up to {np.sum(c)}"
        )
    for iclust in range(u.size):

        # get all points assigned to each cluster:
        cluster_pts = m[ap.labels_ == iclust]
        clusters.append(np.where(ap.labels_ == iclust)[0])

        min_idx = ap.cluster_centers_indices_[iclust]

        # Testing:
        if verb > 1:
            print(
                f"Point in {iclust} center has index {ap.cluster_centers_indices_[iclust]}"
            )
        closest_pt_idx.append(ap.cluster_centers_indices_[iclust])
    return closest_pt_idx, clusters


def agglomerative_clustering(n_clusters, m: np.ndarray, rank=2, verb=0):
    if n_clusters is None:
        mds = MDS(dissimilarity="precomputed", n_components=rank, n_init=50)
        x = mds.fit_transform(m)
        nm = m.shape[0]
        percentages = list(
            set(
                [
                    min(max(int(nm * percentage), 2), 50)
                    for percentage in [0.01, 0.05, 0.1, 0.25, 0.5]
                ]
            )
        )
        gaps = gap(x, nrefs=max(nm, 50), ks=percentages)
        n_clusters = max(percentages[np.argmax(gaps)], 2)
    m = np.ones_like(m) - m
    ac = AgglomerativeClustering(
        n_clusters=n_clusters, affinity="precomputed", linkage="single"
    )
    cm = ac.fit_predict(m)
    clf = NearestCentroid()
    clf.fit(m, cm)
    u, c = np.unique(cm, return_counts=True)
    closest_pt_idx = []
    clusters = []
    if verb > 1:
        print(
            f"{u[-1]+1} unique clusters found: {u} \nWith counts: {c} \nAdding up to {np.sum(c)}"
        )
    for iclust in range(u.size):

        # get all points assigned to each cluster:
        cluster_pts = m[ac.labels_ == iclust]
        clusters.append(np.where(ac.labels_ == iclust)[0])

        # get all indices of points assigned to this cluster:
        cluster_pts_indices = np.where(ac.labels_ == iclust)[0]

        cluster_cen = clf.centroids_[iclust]
        min_idx = np.argmin(
            [euclidean(m[idx], cluster_cen) for idx in cluster_pts_indices]
        )

        # Testing:
        if verb > 1:
            print(
                f"Closest index of point to cluster {iclust} center has index {cluster_pts_indices[min_idx]}"
            )
        closest_pt_idx.append(cluster_pts_indices[min_idx])
    return closest_pt_idx, clusters


def gap(data, refs=None, nrefs=20, ks=range(1, 11)):
    shape = data.shape
    if refs is None:
        tops = data.max(axis=0)
        bots = data.min(axis=0)
        dists = scipy.matrix(scipy.diag(tops - bots))
        rands = scipy.random.random_sample(size=(shape[0], shape[1], nrefs))
        for i in range(nrefs):
            rands[:, :, i] = rands[:, :, i] * dists + bots
    else:
        rands = refs
    gaps = np.zeros((len(ks),))
    for (i, k) in enumerate(ks):
        # (kmc, kml) = scipy.cluster.vq.kmeans2(data, k)
        km = KMeans(n_clusters=k, n_init=5)
        cm = km.fit_predict(data)
        kmc = km.cluster_centers_
        kml = km.labels_
        disp = sum([euclidean(data[m, :], kmc[kml[m], :]) for m in range(shape[0])])
        refdisps = np.zeros((rands.shape[2],))
        for j in range(rands.shape[2]):
            # (kmc, kml) = scipy.cluster.vq.kmeans2(rands[:, :, j], k)
            km = KMeans(n_clusters=k, n_init=5)
            cm = km.fit_predict(rands[:, :, j])
            kmc = km.cluster_centers_
            kml = km.labels_
            refdisps[j] = sum(
                [euclidean(rands[m, :, j], kmc[kml[m], :]) for m in range(shape[0])]
            )
        gaps[i] = scipy.mean(scipy.log(refdisps)) - scipy.log(disp)
    return gaps
