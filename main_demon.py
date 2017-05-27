import argparse
import project
import json
import sys


DISPLAY_COEF = 0.9

args = None


def print_error(description):
    if args.json:
        result = {
            'error': description
        }
        print(json.dumps(result, indent=4))
    else:
        print("Error:", description)


def distance(p1, p2):
    if len(p1) != len(p2):
        print_error("Times mismatch")
        sys.exit(1)
    return sum(map(lambda e: abs(e[0] - e[1])**2, zip(p1, p2)))


def print_clusters_json(clusters):
    result = {
        'result': [
            {
                'name': c['cluster'].name,
                'description': c['cluster'].description,
                'percent': c['percent']
            } for c in clusters
        ]
    }

    print(json.dumps(result, indent=4))
    #print("Cluster {}:\n   name: {}\n  description: {}\n   percent: {:.2f}"
    #      .format(cluster.id, cluster.name, cluster.description, c['percent']*100))


def pretty_print_clusters(clusters):
    print("Clusters ({}):".format(len(clusters)))

    for c in clusters:
        cluster = c['cluster']
        print("  Cluster {}:\n    name: {}\n    description: {}\n    percent: {:.2f}"
              .format(cluster.id, cluster.name, cluster.description, c['percent']))

def calculate_percents(distances):
    result = [{
        'cluster': e[0],
        'distance': e[1],
        'percent': 1.0/(e[1]+1),
    } for e in distances]

    k = 1.0/sum([e['percent'] for e in result])

    for i in range(len(result)):
        result[i]['percent'] *= k

    result.sort(key=lambda e: e['percent'], reverse=True)

    return result


def main():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('-p', type=str, dest='project', help='project file', required=True)
    parser.add_argument('--a', dest='percents', help='show all', action='store_true', default=False)
    parser.add_argument('--json', dest='json', help='Print in json', action='store_true', default=False)
    parser.add_argument('times', metavar='N', type=float, nargs='+', help='times')

    global args
    args = parser.parse_args()

    with open(args.project, 'r') as pfile:
        proj = project.Project(file=pfile)
        distances = [(cluster, distance(cluster.center, args.times)) for cluster in proj.get_clusters()]

        distances.sort(key=lambda e: e[1])

        #print("distances", [e[1] for e in distances])
        clusters = calculate_percents(distances)
        #print('percents', [c['percent'] for c in clusters])

        if args.percents:
            if args.json:
                print_clusters_json(clusters)
            else:
                pretty_print_clusters(clusters)
        else:
            #best_percent = clusters[0]['percent']
            to = len(clusters) - 1
            for i in range(1, len(clusters)):
                if clusters[i-1]['percent'] * DISPLAY_COEF > clusters[i]['percent']:
                    to = i
                    break
            if args.json:
                print_clusters_json(clusters[:to])
            else:
                pretty_print_clusters(clusters[:to])


if __name__ == '__main__':
    main()