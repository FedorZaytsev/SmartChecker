import math
import colorsys
import numpy as np
import sklearn.cluster as cluster
import scipy.spatial as spatial
from sklearn import preprocessing
from sklearn.manifold import TSNE
import pyclustering.cluster.xmeans as pyxmeans
import pyclustering.cluster.kmeans as pykmeans
import fetch


def generate_colors(N):
    HSV_tuples = [(x * 1.0 / N, 1, 1) for x in range(N)]
    return list(map(lambda x: list(colorsys.hsv_to_rgb(*x)) + [1.0], HSV_tuples))


def display_space(X, fig, labels, colors, count_el):
    X = X
    model = TSNE(n_components=3, random_state=0, perplexity=5)
    X = model.fit_transform(X)

    ax = fig.add_subplot(122, projection='3d')

    for cluster in np.unique(labels):
        cluster_els = [el[1] for el in filter(lambda x: x[0] == cluster, zip(labels, X))]

        ax.scatter([el[0] for el in cluster_els][:count_el],
                   [el[1] for el in cluster_els][:count_el],
                   [el[2] for el in cluster_els][:count_el], c=colors[cluster], marker='o', s=16)


    ax.set_label("TSNE")


def tSNE(X, components=3, perplexity=5):
    model = TSNE(n_components=components, random_state=241, perplexity=perplexity)
    return model.fit_transform(X)


def clasterize_n(data, n):
    kmean = cluster.KMeans(n_clusters=n, init='k-means++', random_state=241)
    X = preprocessing.scale(list(map(lambda el: el['time'], data)))
    kmean.fit(X)
    return kmean.labels_

def compute_bic(kmeans, X):
    # http://stats.stackexchange.com/questions/90769/using-bic-to-estimate-the-number-of-k-in-kmeans
    # assign centers and labels
    centers = [kmeans.cluster_centers_]
    labels  = kmeans.labels_
    #number of clusters
    m = kmeans.n_clusters
    # size of the clusters
    n = np.bincount(labels)
    #size of data set
    N, d = X.shape

    #compute variance for all clusters beforehand
    cl_var = (1.0 / (N - m) / d) * sum([sum(spatial.distance.cdist(X[np.where(labels == i)], [centers[0][i]],
             'euclidean')**2) for i in range(m)])

    const_term = 0.5 * m * np.log(N) * (d+1)

    BIC = np.sum([n[i] * np.log(n[i]) -
               n[i] * np.log(N) -
             ((n[i] * d) / 2) * np.log(2*np.pi*cl_var) -
             ((n[i] - 1) * d/ 2) for i in range(m)]) - const_term

    return(BIC)


def get_kmeans(clusters):
    return cluster.KMeans(n_clusters=clusters, init='k-means++', random_state=241, tol=0.1)


def get_affinity_propogation(**kwargs):
    return cluster.AffinityPropagation(**kwargs)


def get_mean_shift(data):
    bandwidth = cluster.estimate_bandwidth(np.array(data), quantile=0.8)
    print('bandwidth', bandwidth)
    return cluster.MeanShift(bandwidth=bandwidth)


def get_dbscan(data):
    return cluster.DBSCAN(min_samples=2, eps=0.5)


def preprocess(data):
    return data#preprocessing.scale(data)


def determinate_number_clusters(data):
    data = data.get_times()
    print("Clusters:")
    bics = []
    ks = []
    for clusters in range(1, 10):
        kmeans = get_kmeans(clusters)
        X = preprocess(data)
        kmeans.fit(X)
        bic = compute_bic(kmeans, X)
        bics.append(bic)
        ks.append(clusters)
        print("{},{:.2f}".format(clusters, bic))


def kmean(data, count):
    km = get_kmeans(count)
    data = data.get_times()
    X = preprocess(data)
    km.fit(X)
    return km.labels_, km.cluster_centers_


def affinity_propogation(data, **kwargs):
    ap = get_affinity_propogation(**kwargs)
    data = data.get_times()
    X = preprocess(data)
    #print('affinity_propogation', X)
    ap.fit(X)
    #print('ap.labels_', ap.labels_)
    return ap.labels_


def mean_shift(data):
    data = data.get_times()
    ms = get_mean_shift(data)
    X = preprocess(data)
    print('mean_shift', X)
    ms.fit(X)
    print('ms.labels_', ms.labels_)
    return ms.labels_


def DBSCAN(data):
    data = data.get_times()
    db = get_dbscan(data)
    X = preprocess(data)
    print('data', data)
    print('X', X)
    db.fit(X)
    print('labels_', db.labels_)
    return db.labels_


def clasterize123123(data):


    for clusters in range(2, 10):
        kmean = cluster.KMeans(n_clusters=clusters, init='k-means++', random_state=241)
        X = preprocessing.scale(list(map(lambda el: el['time'], data)))
        kmean.fit(X)



def pycl2sklearn(data):
    result = [-1 for i in range(max([max(e) for e in data]))]
    for i in range(len(data)):
        for el in data[i]:
            result[el-1] = i

    assert -1 not in result

    return result


def xmeans(data, kmax):
    tests = data.get_times()
    #print("tests({})".format(len(tests)), tests)
    print('kmax', kmax)
    initial_points = tests[:kmax-1]
    print('initial_points', initial_points)
    xmeans_instance = pyxmeans.xmeans(tests, initial_points, ccore=False, kmax=kmax)
    xmeans_instance.process()
    print("done")
    print(len(xmeans_instance.get_clusters()), xmeans_instance.get_clusters())
    print(pycl2sklearn(xmeans_instance.get_clusters()))
    return pycl2sklearn(xmeans_instance.get_clusters())


def distance(p1, p2):
    dist = 0
    assert len(p1) == len(p2)
    for i in range(len(p1)):
        dist += (p1[i] - p2[i])**2

    return dist

def clusterize(data, **kwargs):

    """m = []
    raw = data.get_times()
    for i in range(len(raw)):
        for j in range(len(raw)):
            if i == j:
                continue
            m.append(distance(raw[i], raw[j]))

    min_value = -max(m)
    print('distances max', max(m), 'min', min(m), 'median', np.median(m), 'average', np.average(m))
    print('min', min_value)
    print('')


    for damping in [1 - 1/i for i in range(3, 5)]:
        for preference in [-5 - val*5 for val in range(20)]:
            print('damping {}, preference {}, res {}'.format(damping, preference,
                                          max(affinity_propogation(data, damping=damping, preference=preference))))"""

    #return mean_shift(data)
    #return affinity_propogation(data, damping=0.75, preference=-15)
    return kmean(data, kwargs['kmax'])
    #return DBSCAN(data)
    #return xmeans(data, **kwargs)
