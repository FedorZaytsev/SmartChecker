from numpy.linalg import norm
from sklearn import preprocessing
import math
import os
import json
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from sklearn.manifold import TSNE
import colorsys

def generate_colots(N):
    HSV_tuples = [(x * 1.0 / N, 1, 1) for x in range(N)]
    #return list(map(lambda x: colorsys.hsv_to_rgb(*x), HSV_tuples))
    return list(map(lambda x: colorsys.hsv_to_rgb(*x), HSV_tuples))


def load(folder):
    print("Loading data from {}".format(folder))
    with open(os.path.join(folder, 'statistic')) as f:
        return json.load(f)


def calculate_distance(el1, el2):
    return norm([math.fabs(el1['time'][i] - el2['time'][i]) for i in range(len(el1['time']))])


def tsne(X, perplexity):
    model = TSNE(n_components=3, random_state=0, perplexity=perplexity)
    np.set_printoptions(suppress=True)
    print("preprocessing.scale(X)", preprocessing.scale(X))
    return model.fit_transform(preprocessing.scale(X))


def draw_76_73_74(data, fig, colors):
    ax = fig.add_subplot(231, projection='3d')

    els = [[e['time'][num] for e in data] for num in [76, 73, 74]]

    ax.scatter(els[0], els[1], els[2], c=colors, marker='o')


def display_space(data):
    np.random.seed(241)
    #data = np.random.choice(data, 10, replace=False)
    print("len", len(data))
    X = [el['time'] for el in data]
    print(X)

    colors = generate_colots(len(data))
    fig = plt.figure(figsize=(14, 7))
    draw_76_73_74(data, fig, colors)
    for i, perplexity in enumerate([5, 10, 20, 50, 100]):
        tX = tsne(X, perplexity)
        ax = fig.add_subplot(2, 3, i+2, projection='3d')

        ax.scatter([el[0] for el in tX], [el[1] for el in tX], [el[2] for el in tX], c=colors, marker='o')
        ax.set_title("perplexity {}".format(perplexity))

    plt.show()



def main(data):
    display_space(data)
    return


    distances_between = []
    for i in range(len(data)):
        for j in range(i+1, len(data)):
            if calculate_distance(data[i], data[j]) < 10000000:
                distances_between.append({'el1':data[i], 'el2':data[j], 'dist':calculate_distance(data[i], data[j])})

    distances_zero = []
    for el in data:
        distances_zero.append({'name':el['name'], 'dist':norm(el['time'])})

    average_time = [{'av': np.mean([el['time'][i] for el in data]),
                     'i':i,
                     'time':[math.sqrt(el['time'][i]) for el in data]} for i in range(len(data[0]['time']))]
    average_time.sort(key=lambda x: x['av'], reverse=True)
    print(average_time)


    #print(distances)
    print(list(filter(lambda x: x['dist'] > 100, distances_zero)))

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    ax.scatter(average_time[0]['time'], average_time[1]['time'], average_time[2]['time'], c='red', marker='o')

    ax.set_xlabel('X Label')
    ax.set_ylabel('Y Label')
    ax.set_zlabel('Z Label')

    plt.show()


    #plt.hist(list(map(lambda x: x['dist'], distances_zero)), bins=100)
    #plt.title("Histogram with 'auto' bins")
    #plt.show()









